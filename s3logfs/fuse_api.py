#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

import errno
from datetime import datetime
from stat import *
import math
from time import time
from fusell import FUSELL
from botocore.exceptions import ClientError

from .fs import CheckpointRegion
from .backends import S3Bucket, DiskCache, MemoryCache
from .fs import Log, ReadOnlySegment
from .fs import INode
from .fs import BlockAddress


class FuseApi(FUSELL):

    def __init__(self, mountpoint, bucket, checkpoint_frequency, encoding='utf-8'):
        '''
        This overrides the FUSELL __init__() so that we can set the bucket.
        '''
        self._mount = mountpoint
        self._bucket = bucket
        self._checkpoint_frequency = checkpoint_frequency  # In seconds

        self._CR = CheckpointRegion.from_bytes(self._bucket.get_checkpoint())
        self._roll_forward()
        self._log = Log(
            self._CR.next_segment_id(),
            self._bucket,
            self._CR.block_size,
            self._CR.segment_size
        )

        super().__init__(mountpoint, encoding=encoding)

    ### FUSE METHODS ###

    def destroy(self, userdata):
        print('FS-DESTROY:', userdata)
        """Clean up filesystem

        There's no reply to this method
        """
        self._log.flush()
        self._save_checkpoint()

    def lookup(self, req, parent, name):
        print("FS:LOOKUP", req, parent, name)

        # verify parent inode exists in inode_map lookup
        if self._CR.inode_exists(parent):

            # load parent inode w/ children
            parent_inode = self.load_directory(parent)

            # load child inode with name, and return entry object with attributes
            try:
                child_inode_id = int(parent_inode.children[name])

                # load child inode
                child_inode = self.load_inode(child_inode_id)

                # get child attributes
                attr = child_inode.get_attr()

                entry = dict(
                    ino=child_inode_id,
                    attr=attr,
                    attr_timeout=1.0,
                    entry_timeout=1.0)

                self.reply_entry(req, entry)

            except:
                # No such file or directory if no child found
                self.reply_err(req, errno.ENOENT)
            #else:
            #    # No such file or directory if there is no children data
            #    self.reply_err(req, errno.ENOENT)
        else:
            # No such file or directory if parent does not exist
            self.reply_err(req, errno.ENOENT)

    def forget(self, req, ino, nlookup):
        print('FS-FORGET:', req, ino, nlookup)

        # removes inode form inode_map
        # this is done here because the inode must be
        # maintained until all lookups have been cleared, FUSE
        # calls 'forget' once this occurs.
        # Ex: create directory, cd into directory, delete directory in
        #     another terminal, in first terminal you can still list the
        #     directories contents (though it will show as empty, it wont error)
        #     in the 2nd terminal the directory will no longer show up. Once you
        #     leave the directory on the 1st terminal, forget is called and
        #     deletes the inode
        del self._CR.inode_map[ino]

        # CHECKPOINT
        self._checkpoint_if_necessary()

        self.reply_none(req)

    def getattr(self, req, ino, fi):
        print("FS-GETATTR", req, ino, fi)

        # verify inode exists
        if self._CR.inode_exists(ino):

            # LOAD INODE FROM STORAGE (does not need to be type specific)
            inode = self.load_inode(ino)

            # obtain attr object from inode instance
            attr = inode.get_attr()

            # make sure attr object is not an empty dict()
            if attr:
                self.reply_attr(req, attr, 1.0)
            else:
                self.reply_err(req, errno.ENOENT)
        else:
            # No file or directory, inode was not found
            self.reply_err(req, errno.ENOENT)


    def setattr(self, req, ino, attr, to_set, fi):
        print('FS-SETATTR:', req, ino, attr, to_set, fi)

        # verify inode exists
        if self._CR.inode_exists(ino):

            # LOAD INODE FROM STORAGE
            inode = self.load_inode(ino)

            if inode.get_attr():

                # iterate through to_set key's to update inode
                for key in to_set:
                    # handle st_mode
                    if key == "st_mode":
                        # keep current IFMT, replace IMODE
                        inode.mode = S_IFMT(
                            inode.mode) | S_IMODE(attr["st_mode"])
                        inode.status_last_changed_at = time()
                    elif key == "st_size":
                        inode.size = attr["st_size"]
                    elif key == "st_blocks":
                        inode.block_count = attr["st_blocks"]
                    elif key == "st_blksize":
                        inode.block_size = attr["st_blksize"]
                    elif key == "st_nlink":
                        inode.hard_links = attr["st_nlink"]
                    elif key == "st_uid":
                        inode.uid = attr["st_uid"]
                        inode.status_last_changed_at = time()
                    elif key == "st_gid":
                        inode.gid = attr["st_gid"]
                        inode.status_last_changed_at = time()
                    elif key == "st_atime":
                        inode.last_accessed_at = attr["st_atime"]
                        inode.status_last_changed_at = time()
                    elif key == "st_mtime":
                        inode.last_modified_at = attr["st_mtime"]
                        inode.status_last_changed_at = time()
                    elif key == "st_ctime":
                        inode.status_last_changed_at = time()
                    elif key == "st_dev":
                        inode.size = attr["st_dev"]
                    elif key == "st_rdev":
                        inode.size = attr["st_rdev"]

                # write modified INODE to storage
                self.write_inode(inode)

                # CHECKPOINT
                self._checkpoint_if_necessary()

                # get modified attr object
                inode_attr = inode.get_attr()

                # return reply_attr wtih modified inode_attr
                self.reply_attr(req, inode_attr, 1.0)
            else:
                self.reply_err(req, errno.ENOENT)
        else:
            self.reply_err(req, errno.ENOENT)


    def mknod(self, req, parent, name, mode, rdev):
        print('FS-MKNOD:', req, parent, name,  mode, rdev)

        # verify inode exists
        if self._CR.inode_exists(parent):

            # 1. load directory
            directory = self.load_directory(parent)

            # 2. CREATE NEW FILE INODE
            new_node = INode()
            new_node.inode_number = self._CR.next_inode_id()

            # - obtain uid/gid info via req
            ctx = self.req_ctx(req)
            new_node.uid = ctx['uid']
            new_node.gid = ctx['gid']

            # - set mode
            new_node.mode = mode

            # - set hard links to 1, for itself
            new_node.hard_links = 1

            # - set time attributes
            now = time()
            new_node.last_accessed_at = now
            new_node.last_modified_at = now
            new_node.status_last_changed_at = now

            # set rdev
            new_node.rdev = rdev

            # 4. WRITE NEW NODE
            self.write_inode(new_node)

            # 3. update parent <> new child relationship
            # - increment hard_links by 1
            directory.hard_links += 1

            # - add new node to directory
            directory.children[name] = new_node.inode_number

            # 5. WRITE PARENT AND UPDATE INODE_MAP
            # - write parent data to log
            self.write_directory(directory)
 
            # 6. checkpoint if needed
            self._checkpoint_if_necessary()

            # 7. Create/Return entry object
            # - get new_node attr object
            attr = new_node.get_attr()

            if attr:
                # - create entry
                entry = dict(ino=new_node.inode_number,
                             attr=attr,
                             attr_timeout=1.0,
                             entry_timeout=1.0)
                # reply with entry
                self.reply_entry(req, entry)
            else:
                # I/O error, was unable to get attributes for new inode
                self.reply_err(req, errno.EIO)
        else:
            # I/O error, parent does not exist to create node
            self.reply_err(req, errno.EIO)


    def mkdir(self, req, parent, name, mode):
        print('FS-MKDIR:', parent, name, mode)

        # verify inode exists
        if self._CR.inode_exists(parent):

            # 1. LOAD CURRENT DIRECTORY w/ children
            current_directory = self.load_directory(parent)

            # 2. CREATE NEW DIRECTORY INODE
            newdir = INode()

            # - obtain new inodeid from CheckpointRegion
            newdir.inode_number = self._CR.next_inode_id()

            # - set mode
            newdir.mode = S_IFDIR | mode

            # - set size / block info
            newdir.size = self._log.get_block_size()
            newdir.block_count = int(self._log.get_block_size() / 512)
            newdir.block_size = self._log.get_block_size()

            # - obtain uid/gid info via req
            ctx = self.req_ctx(req)
            newdir.uid = ctx['uid']
            newdir.gid = ctx['gid']

            # - set parent (only used for directories, files can have multiple parents via hard links)
            newdir.parent = parent

            # - set hard links to 2 (for "." and "..")
            newdir.hard_links = 2

            # - set time attributes
            now = time()
            newdir.last_accessed_at = now
            newdir.last_modified_at = now
            newdir.status_last_changed_at = now

            # 3. update parent <> child relationship
            # - increment hard_links by 1
            current_directory.hard_links += 1
            # - add new directory to children
            current_directory.children[name] = newdir.inode_number

            # 4. WRITE NEW DIRECTORY AND UPDATE INODE_MAP
            self.write_directory(newdir)

            # 5. WRITE PARENT AND UPDATE INODE_MAP
            self.write_directory(current_directory)

            # 6. CHECKPOINT
            self._checkpoint_if_necessary()

            # 7. Create/Return entry object
            # - get newdir attr object
            attr = newdir.get_attr()

            if attr:
                # - create entry
                entry = dict(ino=newdir.inode_number,
                             attr=attr,
                             attr_timeout=1.0,
                             entry_timeout=1.0)
                # reply with entry
                self.reply_entry(req, entry)
            else:
                # I/O error, was not able to obtain attr for new directory
                self.reply_err(req, errno.EIO)
        else:
            # I/O error, parent does not exist to create node
            self.reply_err(req, errno.EIO)

    def unlink(self, req, parent, name):
        print('FS-UNLINK:', req, parent, name)

        # verify inode exists
        if self._CR.inode_exists(parent):

            # 1. LOAD DIRECTORY
            directory = self.load_directory(parent)

            # remove inode from parents children
            inode_id = directory.children.pop(name)

            # write directory
            self.write_directory(directory)

            # update inode, decrement hard link and update last changed
            inode = self.load_inode(inode_id)
            inode.hard_links -= 1
            inode.status_last_changed_at = time()
            self.write_inode(inode)

            # NOTE: we do not remove the unlinked inode from the inode_map here
            #       it should be handled by the forget call

            self._checkpoint_if_necessary()

            # return no error to indicate success
            self.reply_err(req, 0)

        else:
            # I/O error parent does not exist
            self.reply_err(req, errno.EIO)

    def rmdir(self, req, parent, name):
        print("FS-RMDIR:", req, parent, name)

        # verify inode exists
        if self._CR.inode_exists(parent):

            # 1. LOAD CURRENT DIRECTORY
            current_directory = self.load_directory(parent)

            # remove directory from parents children
            inode = current_directory.children.pop(name)

            # decrement parent hard_links
            current_directory.hard_links -= 1

            # write current directory
            self.write_directory(current_directory)

            # CHECKPOINT
            self._checkpoint_if_necessary()

            # return no error
            self.reply_err(req, 0)

        else:
            # I/O error parent does not exist
            self.reply_err(req, errno.EIO)

    def rename(self, req, parent, name, newparent, newname):
        print('FS-RENAME:', req, parent, name, newparent, newname)

        # load current directory
        current_directory = self.load_directory(parent)

        # when parent is same as new parent, update directory name in parent
        # when not the same, remove from parent, add to newparent
        if (parent == newparent):

            # pop child with name from parent
            inode = current_directory.children.pop(name)

            # add child with newname to parent's children
            current_directory.children[newname] = inode

            # write current directory
            self.write_directory(current_directory)

        else:

            # load new directory
            new_directory = self.load_directory(newparent)

            # remove child with name from current directory
            inode = current_directory.children.pop(name)

            # add child with newname to newparent
            new_directory.children[newname] = inode

            # write current directory
            self.write_directory(current_directory)

            # write newparent data
            self.write_directory(new_directory)

        # checkpoint
        self._checkpoint_if_necessary()

        # return no error
        self.reply_err(req, 0)


    def link(self, req, ino, newparent, newname):
        print('FS-LINK:', req, ino, newparent, newname)

        # 1. LOAD DIRECTORY
        directory = self.load_directory(newparent)

        # - add newname to directory
        directory.children[newname] = ino

        # - increase directory hard links
        directory.hard_links += 1

        # 2. LOAD TARGET FILE
        target_file = self.load_inode(ino)

        # - increase target files hard links (since there are 2 hard links to file)
        target_file.hard_links += 1
        target_file.status_last_changed_at = time()

        # 3. WRITE TARGET FILE INODE
        self.write_inode(target_file)

        # 4. WRITE DIRECTORY TO LOG & UPDATE inode map
        self.write_directory(directory)

        # 5. CHECKPOINT
        self._checkpoint_if_necessary()

        # 6. RETURN ENTRY FOR INODE W/ ATTRIBUTES
        attr = target_file.get_attr()

        if attr:
            # - create entry
            entry = dict(ino=target_file.inode_number,
                         attr=attr,
                         attr_timeout=1.0,
                         entry_timeout=1.0)
            # reply with entry
            self.reply_entry(req, entry)
        else:
            return dict()

    def open(self, req, ino, fi):
        print('FS-OPEN:', req, ino)

        # verify inode exists, return open reply or error
        if self._CR.inode_exists(ino):

            # load inode
            inode = self.load_inode(ino)

            # update access time
            now = time()
            inode.last_accessed_at = now

            # write inode
            self.write_inode(inode)

            self.reply_open(req, fi)
        else:
            self.reply_err(req, errno.EIO)

    def read(self, req, ino, size, off, fi):
        print('read:', req, ino, size, off)

        # verify inode exists
        if self._CR.inode_exists(ino):

            # 1. LOAD INODE
            inode = self.load_inode(ino)

            if inode.size > 0:
           
                # read data from file
                data = self.read_file(inode, size, off)

                # return exact number of bytes
                self.reply_buf(req, data[0:size])

            else:
                self.reply_buf(req, b'')

        else:
            self.reply_err(req, errno.ENOENT)

    def write(self, req, ino, buf, off, fi):
        print('FS-WRITE:', req, ino, len(buf), off)

        # verify inode exists
        if self._CR.inode_exists(ino):

            # 1. LOAD FILE
            inode = self.load_inode(ino)

            # 2. WRITE FILE DATA TO LOG
            self.write_file(inode, buf, off)

            # 3. CHECKPOINT
            self._checkpoint_if_necessary()

            # return the length of the data written
            self.reply_write(req, len(buf))

        else:
            # inode does not exist to write too
            self.reply_err(req, errno.ENOENT)

    def readdir(self, req, ino, size, off, fi):
        print('FS-READDIR:', req, ino, size, off, fi)

        # 1. LOAD DIRECTORY INODE
        directory = self.load_directory(ino)

        # 2. BUILD DEFUALT LIST OF ENTRIES
        entries = [
            ('.', {'st_ino': directory.inode_number, 'st_mode': S_IFDIR}),
            ('..', {'st_ino': directory.parent, 'st_mode': S_IFDIR})]

        # 3. ADD CHILDREN TO LIST
        for k, v in directory.children.items():
            # when trying to load inode, if it fails because
            # it is not in the inode_map, we don't want to include
            # it with the entries
            try:
                # load child inode
                child_inode = self.load_inode(int(v))
                # get child name
                child_name = k
                # set attr object
                child_attr = child_inode.get_attr()
                # add inode/attr to entries
                entries.append((child_name, child_attr))
            except:
                print("INode(", int(v), "=", k, ") not found!")

        self.reply_readdir(req, size, off, entries)

    def symlink(self, req, link, parent, name):
        print('symlink:', req, link, parent, name)

        # create symlink inode
        link_node = INode()
        link_node.inode_number = self._CR.next_inode_id()

        # - obtain uid/gid info via req
        ctx = self.req_ctx(req)
        link_node.uid = ctx['uid']
        link_node.gid = ctx['gid']

        # - set mode to S_IFLNK w/ 777 permissions
        link_node.mode = S_IFLNK | 0o777
      
        # - set hard links to 1, for itself
        link_node.hard_links = 1

        # - set time attributes
        now = time()
        link_node.last_accessed_at = now
        link_node.last_modified_at = now
        link_node.status_last_changed_at = now

        # write symlink to log
        self.write_symlink(link_node, link)

        # load directory
        directory = self.load_directory(parent)
        
        # update parent
        directory.children[name] = link_node.inode_number

        # write directory to log
        self.write_directory(directory)

        # - get newdir attr object
        attr = link_node.get_attr()

        if attr:
            # - create entry
            entry = dict(ino=link_node.inode_number,
                         attr=attr,
                         attr_timeout=1.0,
                         entry_timeout=1.0)
            # reply with entry
            self.reply_entry(req, entry)
        else:
            # I/O error, was not able to obtain attr for new directory
            self.reply_err(req, errno.EIO)


    def readlink(self, req, ino):
        print('readlink:', req, ino)

        # load inode
        inode = self.load_inode(ino)

        # read link from inode data
        link = self.read_symlink(inode)

        # reply with link
        self.reply_readlink(req, link)

    # ************
    # adding other possible functions which we may need to implement
    # based on the fusell.py code and libfuse library information
    # ************

    def release(self, req, ino, fi):
        print('FS-RELEASE:', req, ino, fi)

        # for the type of file system we have , we won't need to implement
        # this function beyond checking if a checkpoint is necessary.

        self._checkpoint_if_necessary()

        # return no error
        self.reply_err(req, 0)

    def flush(self, req, ino, fi):
        print('flush:', req, ino, fi)

        # error because its not implemented
        self.reply_err(req, errno.ENOSYS)

    def statfs(self, req, ino):
        print('statfs:', req, ino)

        stat_fs_info = dict()
        stat_fs_info["f_bavail"] = 0
        stat_fs_info["f_bfree"] = 0
        stat_fs_info["f_blocks"] = 0
        stat_fs_info["f_bsize"] = 0
        stat_fs_info["f_favail"] = 0
        stat_fs_info["f_ffree"] = 0
        stat_fs_info["f_files"] = 0
        stat_fs_info["f_flag"] = 0
        stat_fs_info["f_frsize"] = 0
        stat_fs_info["f_namemax"] = 255

        # appears that this funciton is not implemented
        # in fusell and possibly in libfuse, need to research more

        # error because its not implemented
        self.reply_err(req, errno.ENOSYS)

    def listxattr(self, req, ino, size):
        print('listxattr:', req, ino, size)

        # error because its not implemented
        self.reply_err(req, errno.ENOTSUP)

    def setxattr(self, req, ino, name, value, size, flags):
        print('setxattr:', req, ino, name, value, size, flags)

        # error because its not implemented
        self.reply_err(req, errno.ENOTSUP)

    def getxattr(self, req, ino, name, size):
        print('getxattr:', req, ino, name, size)

        # error because its not implemented
        self.reply_err(req, errno.ENOTSUP)

    def removexattr(self, req, ino, name):
        print('removexattr:', req, ino, name)

        # error because its not implemented
        self.reply_err(req, errno.ENOSYS)


# following functions may not be required, but if we have time we can implement
# them for more functionality

# def opendir(self, req, ino, fi):
##        print('opendir:', req, ino, fi)
# error because its not implemented
# self.reply_err(req,errno.ENOSYS)

# def releasedir(self, req, ino, fi):
##        print('releasedir:', req, ino, fi)
# error because its not implemented
# self.reply_err(req,errno.ENOSYS)

    def fsync(self, req, ino, datasync, fi):
        """Synchronize file contents

        Valid replies:
            reply_err
        """

        self._log.flush()

# def fsyncdir(self, req, ino, datasync, fi):
##        print('fsyncdir:', req, ino, datasync, fi)
# return no error
# self.reply_err(req,0)


### Helper methods ###

    # this method will load a directory inode from the log
    # it can optionally not load children if they are not needed
    def load_directory(self, inode_id, load_children=True):

        # load inode from inode_id
        inode = self.load_inode(inode_id)

        # load directory data and set children
        if load_children:
            data = bytearray()
            for x in range(int(inode.size / inode.block_size)):
                data = self.read_data_block(inode, data, x)

            if len(bytes(data)) > 0:
                inode.bytes_to_children(bytes(data))

        # return created inode
        return inode

    # this method will write a directory inode to the log
    def write_directory(self, inode, write_children=True):
        
        # there could be situations where the contents of a directory do not
        # change, but its attributes do.
        if write_children:

            # get inode data & set size/block_count attributes
            data = inode.children_to_bytes()
            number_blocks = math.ceil(len(data)/self._log.get_block_size())
            # directory size is always an increment of system block_size (page_size)
            inode.size = number_blocks * self._log.get_block_size()
            inode.block_count = int(inode.size / 512)

            # iterate through data block by block and write to log
            for x in range(number_blocks):
                inode = self.write_data_block(inode, data, x)

        # - write inode to log
        self.write_inode(inode)

    # this method will write a directory inode to the log
    def write_symlink(self, inode, link):
        
        # get inode data & set size/block_count attributes
        data = link.encode('utf-8')
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        # directory size is always an increment of system block_size (page_size)
        inode.size = len(data)
        inode.block_count = int(inode.size / 512)

        # iterate through data block by block and write to log
        for x in range(number_blocks):
            inode = self.write_data_block(inode, data, x)

        # - write inode to log
        self.write_inode(inode)

    def read_symlink(self, inode):
        block_count = math.ceil(inode.size / self._log.get_block_size())
        data = bytearray()
        for x in range(block_count):
            data = self.read_data_block(inode, data, x)

        link = data.decode('utf-8')[0:inode.size]
        
        return link


    # read_file - will return data from a file, based on the size an offset
    def read_file(self, inode, size, offset):

        data = bytearray()

        if size>0:

            # determine number of blocks of data to read based on requetsed size
            block_count = math.ceil(size / self._log.get_block_size())

            # define file_offset , offset should be divisible by our block_size
            file_offset = offset // self._log.get_block_size()

            # load data into byte array, then return requested bytes
            for x in range(block_count):
                data = self.read_data_block(inode, data, x, file_offset)

        # return bytes
        return bytes(data)


    def write_file(self, inode, buf, off):

        # determine number of blocks to write
        block_count = math.ceil(len(buf) / self._log.get_block_size())

        # get file_offset, off should be evenly divisible by block_size
        file_offset = off // self._log.get_block_size()

        # furthest write, will be used to set new size
        for x in range(block_count):
            inode = self.write_data_block(inode, buf, x, file_offset)

        # 3. Increase Size attribute if file grew
        max_write_size = len(buf) + (file_offset *
                                     self._log.get_block_size())
        if (max_write_size > inode.size):
            inode.size = max_write_size
            inode.block_count = math.ceil(max_write_size / 512)

        # update modified attr
        now = time()
        inode.last_modified_at = now
        inode.status_last_changed_at = now

        # 3. Write Inode to log
        self.write_inode(inode)
 

    def write_inode(self, inode):

        # write inode to log
        inode_addr = self._log.write_inode(inode.to_bytes(), inode.inode_number)

        # - update CR inode_map for inode
        self._CR.inode_map[inode.inode_number] = inode_addr

    # method writes a single block to log, and updates inode address info
    def write_data_block(self, inode, data, x, file_offset=0):
        start = x * self._log.get_block_size()
        end = (x + 1) * self._log.get_block_size()
        block = data[start:end]
        address = self._log.write_data_block(block)
        inode.write_address(address, file_offset + x)
        return inode

    def read_data_block(self, inode, data, x, file_offset=0):
        block_address = inode.read_address(file_offset + x)
        data.extend(self._log.read_block(block_address))
        return data

    def load_inode(self, inode_id):
        # obtain inode address from imap
        try:
            inode_address = self._CR.inode_map[inode_id]
        except:
            print("INode (", inode_id, ") not found in inode_map!")

        # define default inode
        inode = INode()

        # read inode data from log
        inode_data = self._log.read_block(inode_address)

        # load inode from log
        return inode.from_bytes(inode_data)

    def _checkpoint_if_necessary(self):
        current_time = int(time())
        last_checkpoint_time = self._CR.time()

        if (current_time - last_checkpoint_time) >= self._checkpoint_frequency:
            self._log.flush()
            self._save_checkpoint()

    def _save_checkpoint(self):
        last_segment_id = self._log.get_current_segment_id() - 1
        self._CR.set_segment_id(last_segment_id)
        self._CR.set_time(int(time()))
        serialized_checkpoint = self._CR.to_bytes()
        self._bucket.put_checkpoint(serialized_checkpoint)

    def _roll_forward(self):
        '''
        Checks for segments > the checkpoint's segment id and updates the imap
        with any inodes they contain.
        '''
        last_segment_id = self._CR.current_segment_id()
        last_segment_exists = True

        while last_segment_exists:
            current_segment_id = last_segment_id + 1

            try:
                segment_bytes = self._bucket.get_segment(current_segment_id)
                self._update_imap_from_segment(
                    current_segment_id, segment_bytes)
            except ClientError:
                last_segment_exists = False

            last_segment_id = current_segment_id

        self._CR.set_segment_id(last_segment_id - 1)

    def _update_imap_from_segment(self, segment_id, segment_bytes):
        segment = ReadOnlySegment(
            segment_bytes,
            segment_id,
            self._CR.block_size,
            self._CR.segment_size
        )

        for (inode_number, block_number) in segment.inode_block_numbers():
            self._CR.inode_map[inode_number] = BlockAddress(
                segment_id, block_number)
