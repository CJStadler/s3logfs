#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

import errno
from datetime import datetime
from stat import *
import math
from time import time
from fusell import FUSELL

from .fs import CheckpointRegion
from .backends import S3Bucket, DiskCache, MemoryCache
from .fs import Log
from .fs import INode
from .fs import BlockAddress


class FuseApi(FUSELL):

    def __init__(self, mountpoint, bucket, encoding='utf-8'):
        '''
        This overrides the FUSELL __init__() so that we can set the bucket.
        '''

        # mount point
        self._mount = mountpoint

        self._bucket = bucket

        self.checkpoint_frequency = 30  # In seconds

        super().__init__(mountpoint, encoding=encoding)

    def init(self, userdata, conn):
        print("FS:INIT")

        # init superblock

        # init CheckpointRegion - new FS, no recovery yet
        self._CR = CheckpointRegion(self._bucket.name(), 0)

        # store superblock in CheckpointRegion

        # init Log
        self._log = Log(
                      self._CR.next_segment_id(),
                      self._bucket,
                      self._CR.block_size,
                      self._CR.segment_size)

        # need to init empty file system
        # 1. create root inode
        root_inode = INode()
        root_inode.inode_number = self._CR.next_inode_id()
        root_inode.parent = root_inode.inode_number
        root_inode.mode = S_IFDIR | 0o777        # directory with 777 chmod
        root_inode.hard_links = 2     # "." and ".." make the first 2 hard links

        # 2. write root inode directory data to log
        # -- convert children to bytes
        data = root_inode.children_to_bytes()
        # -- cut bytes up into block_size units and write each
        # -- unit storing addr to inode
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        root_inode.size = number_blocks * self._log.get_block_size()
        print("ROOT SIZE", root_inode.size)
        root_inode.block_count = int(root_inode.size / 512)
        root_inode.block_size = self._log.get_block_size()
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write_block(block)
            root_inode.write_address(address)

        # 3. write root inode to log
        root_inode_addr = self._log.write_block(root_inode.to_bytes())
        # 4. update CR inode_map to for "/"
        self._CR.inode_map[root_inode.inode_number] = root_inode_addr
        # 5. update CR root_inode_id for "/"
        self._CR.root_inode_id = root_inode.inode_number

    def load_inode(self, inode_id):
        # obtain inode address from imap
        inode_address = self._CR.inode_map[inode_id]

        # define default inode
        inode = INode()

        # read inode data from log
        inode_data = self._log.read_block(inode_address)

        # load inode from log
        return inode.from_bytes(inode_data)

    def destroy(self, userdata):
        print('destroy:',userdata)
        """Clean up filesystem

        There's no reply to this method
        """
        self._save_checkpoint()
        self._log.flush()

    def lookup(self, req, parent, name):
        print("FS:lookup", parent, name)

        # load parent inode
        parent_inode = self.load_inode(parent)

        # load directory children
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            addr = parent_inode.read_address(x)
            data.extend(self._log.read_block(addr))
        parent_inode.bytes_to_children(bytes(data))

        # obtain child inodeid via name, if this fails, it should return an empty dict()
        try:
            child_inode_id = int(parent_inode.children[name])

            # load child inode
            child_inode = self.load_inode(child_inode_id)

            # get child attributes
            attr = child_inode.get_attr()
        except:
            attr = dict()

        # return entry object for child
        if attr:
            entry = dict(
                ino=child_inode_id,
                attr=attr,
                attr_timeout=1.0,
                entry_timeout=1.0)
            self.reply_entry(req, entry)
        else:
            self.reply_err(req, errno.ENOENT)

    def forget(self, req, ino, nlookup):
        print('forget:', req, ino, nlookup)

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

        self.reply_none(req)

    def getattr(self, req, ino, fi):
        print("FS:getattr", ino)

        # LOAD INODE FROM STORAGE
        inode = self.load_inode(ino)

        # obtain attr object from inode instance
        attr = inode.get_attr()

        # RETURN ATTR OBJECT
        if attr:
            self.reply_attr(req, attr, 1.0)
        else:
            self.reply_err(req, errno.ENOENT)

    def setattr(self, req, ino, attr, to_set, fi):
        print('setattr:', ino, to_set)

        # LOAD INODE FROM STORAGE
        inode = self.load_inode(ino)

        if inode.get_attr():
            # iterate through to_set key's to update inode
            for key in to_set:
                # handle st_mode
                if key == "st_mode":
                    # keep current IFMT, replace IMODE
                    inode.mode = S_IFMT(inode.mode) | S_IMODE(attr["st_mode"])
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
                elif key == "st_gid":
                    inode.gid = attr["st_gid"]
                elif key == "st_atime":
                    inode.last_accessed_at = attr["st_atime"]
                elif key == "st_mtime":
                    inode.last_modified_at = attr["st_mtime"]
                elif key == "st_ctime":
                    inode.status_last_changed_at = attr["st_ctime"]
                elif key == "st_dev":
                    inode.size = attr["st_dev"]
                elif key == "st_rdev":
                    inode.size = attr["st_rdev"]

            # write modified INODE to storage
            inode_addr = self._log.write_block(inode.to_bytes())

            # update CR inode_map address
            self._CR.inode_map[inode.inode_number] = inode_addr
            self._checkpoint_if_necessary()

            # get modified attr object
            inode_attr = inode.get_attr()

            # return reply_attr wtih modified inode_attr
            self.reply_attr(req, inode_attr, 1.0)
        else:
            self.reply_err(req, errno.ENOENT)

    def mknod(self, req, parent, name, mode, rdev):
        print('mknod:', parent, name)

        # 1. CREATE NEW FILE INODE
        new_node = INode()
        new_node.inode_number = self._CR.next_inode_id()

        # - obtain uid/gid info via req
        ctx = self.req_ctx(req)
        new_node.uid = ctx['uid']
        new_node.gid = ctx['gid']

        # - set mode
        new_node.mode = mode

        # - set parent
        new_node.parent = parent

        # - set hard links to 2 (for "." and "..")
        new_node.hard_links = 1

        # - set time attributes
        now = time()
        new_node.last_accessed_at = now
        new_node.last_modified_at = now
        new_node.status_last_changed_at = now

        # set rdev
        new_node.rdev = rdev

        # 2. LOAD PARENT INODE
        # - load inode
        parent_inode = self.load_inode(parent)
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read_block(parent_inode.read_address(x)))
        parent_inode.bytes_to_children(bytes(data))
        # - increment hard_links by 1
        parent_inode.hard_links += 1
        # - add new directory to children
        parent_inode.children[name] = new_node.inode_number

        # 3. WRITE NEW DIRECTORY AND UPDATE INODE_MAP
        # - write new_node data to log
        data = new_node.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        for x in range(number_blocks):
            start = x*self._log.get_block_size()
            end = (x+1)*self._log.get_block_size()
            block = data[start:end]
            address = self._log.write_block(block)
            new_node.write_address(address,x)
        # - write new_node inode to log
        new_inode_addr = self._log.write_block(new_node.to_bytes())
        # update CR inode_map for new_node
        self._CR.inode_map[new_node.inode_number] = new_inode_addr

        # 4. WRITE PARENT AND UPDATE INODE_MAP
        # - write parent data to log
        data = parent_inode.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        parent_inode.size = number_blocks * self._log.get_block_size()
        parent_inode.block_count = int(parent_inode.size / 512)
        for x in range(number_blocks):
            start = x*self._log.get_block_size()
            end = (x+1)*self._log.get_block_size()
            block = data[start:end]
            address = self._log.write_block(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write_block(parent_inode.to_bytes())
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr
        self._checkpoint_if_necessary()

        # 5. Create/Return entry object
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
            # reply with error
            self.reply_err(req, errno.EROFS)

    def mkdir(self, req, parent, name, mode):
        print('mkdir:', parent, name, mode)

        # 1. CREATE NEW DIRECTORY INODE
        # - create new directory inode
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

        # - set parent
        newdir.parent = parent

        # - set hard links to 2 (for "." and "..")
        newdir.hard_links = 2

        # 2. LOAD PARENT INODE
        # - load inode
        parent_inode = self.load_inode(parent)
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read_block(parent_inode.read_address(x)))
        parent_inode.bytes_to_children(bytes(data))
        # - increment hard_links by 1
        parent_inode.hard_links += 1
        # - add new directory to children
        parent_inode.children[name] = newdir.inode_number

        # 3. WRITE NEW DIRECTORY AND UPDATE INODE_MAP
        # - write newdir data to log
        data = newdir.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write_block(block)
            newdir.write_address(address,x)
        # - write newdir inode to log
        newdir_inode_addr = self._log.write_block(newdir.to_bytes())
        # update CR inode_map for newdir
        self._CR.inode_map[newdir.inode_number] = newdir_inode_addr

        # 4. WRITE PARENT AND UPDATE INODE_MAP
        # - write parent data to log
        data = parent_inode.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        parent_inode.size = number_blocks * self._log.get_block_size()
        parent_inode.block_count = int(parent_inode.size / 512)
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write_block(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write_block(parent_inode.to_bytes())
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr
        self._checkpoint_if_necessary()

        # 5. Create/Return entry object
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
            # reply with error
            self.reply_err(req, errno.EROFS)

    def unlink(self, req, parent, name):
        print('unlink:', req, parent, name)

        # 1. LOAD PARENT INODE
        # - load inode
        parent_inode = self.load_inode(parent)
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read_block(parent_inode.read_address(x)))
        parent_inode.bytes_to_children(bytes(data))

        # remove inode from parents children
        inode = parent_inode.children.pop(name)

        # write parent data
        data = parent_inode.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        parent_inode.size = number_blocks * self._log.get_block_size()
        parent_inode.block_count = int(parent_inode.size / 512)
        for x in range(number_blocks):
            start = x*self._log.get_block_size()
            end = (x+1)*self._log.get_block_size()
            block = data[start:end]
            address = self._log.write_block(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write_block(parent_inode.to_bytes())
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr

        # NOTE: we do not remove the unlinked inode from the inode_map here
        #       it should be handled by the forget call

        self._checkpoint_if_necessary()

        # return no error
        self.reply_err(req, 0)

        #self.reply_err(req, errno.EROFS)

    def rmdir(self, req, parent, name):

        # 1. LOAD PARENT INODE
        # - load inode
        parent_inode = self.load_inode(parent)
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read_block(parent_inode.read_address(x)))
        parent_inode.bytes_to_children(bytes(data))

        # remove directory from parents children
        inode = parent_inode.children.pop(name)

        # decrement parent hard_links
        parent_inode.hard_links -= 1

        # write parent data
        data = parent_inode.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        parent_inode.size = number_blocks * self._log.get_block_size()
        parent_inode.block_count = int(parent_inode.size / 512)
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write_block(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write_block(parent_inode.to_bytes())
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr

        self._checkpoint_if_necessary()

        # return no error
        self.reply_err(req, 0)

    def rename(self, req, parent, name, newparent, newname):
        print('rename:',req,parent,name,newparent,newname)
        """Rename a file

        Valid replies:
            reply_err
        """
        self._checkpoint_if_necessary()
        self.reply_err(req, 0)

    def link(self, req, ino, newparent, newname):
        print('link:',req,ino,newparent,newname)
        """Create a hard link

        Valid replies:
            reply_entry
            reply_err
        """
        self._checkpoint_if_necessary()
        self.reply_err(req, errno.EROFS)

    def open(self, req, ino, fi):
        print('open:', req, ino)

        # verify inode exists, return open reply or error
        if self._CR.inode_exists(ino):
            self.reply_open(req, fi)
        else:
            self.reply_err(req, errno.EIO)

    def read(self, req, ino, size, off, fi):
        print('read:', req, ino, size, off)
        """Read data

        Valid replies:
            reply_buf
            reply_err
        """
        self.reply_err(req, errno.EIO)

    def write(self, req, ino, buf, off, fi):
        print('write:', req, ino, len(buf), off)

        # 1. LOAD INODE
        inode = self.load_inode(ino)

        # 2. Write buffer (buf) to log in blocksize units updating
        #    block_addresess in inode to reflect data positioning in file.
        block_count = math.ceil(len(buf) / self._log.get_block_size())
        # -- get file_offset, off should be evenly divisible by block_size
        file_offset = off // self._log.get_block_size()
        # furthest write
        write_offset = 0
        for x in range(block_count):
            start = x*self._log.get_block_size()
            end = (x+1)*self._log.get_block_size()
            block = buf[start:end]
            address = self._log.write_block(block)
            inode.write_address(address, file_offset + x)

        # 3. Increase Size attribute if file grew
        max_write_size = len(buf) + (file_offset * self._log.get_block_size())
        if (max_write_size > inode.size):
            inode.size = max_write_size
            inode.block_count = math.ceil(max_write_size / 512)

        # 3. Write Inode to log
        inode_addr = self._log.write_block(inode.to_bytes())

        # 4. Update CR Inode Map
        self._CR.inode_map[ino] = inode_addr

        self._checkpoint_if_necessary()

        self.reply_write(req, len(buf))

        # self.reply_err(req, errno.EROFS)

    def readdir(self, req, ino, size, off, fi):
        print('readdir:', ino)

        # 1. LOAD DIRECTORY INODE
        directory = self.load_inode(ino)
        data = bytearray()
        number_blocks = int(directory.size / directory.block_size)
        for x in range(number_blocks):
            data.extend(self._log.read_block(directory.read_address(x)))
        directory.bytes_to_children(bytes(data))

        # 2. BUILD DEFUALT LIST OF ENTRIES
        entries = [
            ('.', {'st_ino': directory.inode_number, 'st_mode': S_IFDIR}),
            ('..', {'st_ino': directory.parent, 'st_mode': S_IFDIR})]

        # 3. ADD CHILDREN TO LIST
        for k,v in directory.children.items():
            # load child inode
            child_name = k
            child_inode = self.load_inode(int(v))
            # set attr object
            child_attr = child_inode.get_attr()
            # add inode/attr to entries
            entries.append((child_name,child_attr))

        self.reply_readdir(req, size, off, entries)

    def access(self, req, ino, mask):
        print('access:', req, ino, mask)
        """Check file access permissions

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.ENOSYS)

    def create(self, req, parent, name, mode, fi):
        print('create:',req,parent,name,mode)
        """Create and open a file

        Valid replies:
            reply_create
            reply_err
        """
        self._checkpoint_if_necessary()
        self.reply_err(req, errno.ENOSYS)

    # ************
    # adding other possible functions which we may need to implement
    # based on the fusell.py code and libfuse library information
    # ************

    def readlink(self, req, ino):
        print('readlink:', req, ino)

        # error because its not implemented
        self.reply_err(req,errno.ENOENT)

    def release(self, req, ino, fi):
        print('release:', req, ino, fi)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def flush(self, req, ino, fi):
        print('flush:', req, ino, fi)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def statfs(self, req, ino):
        print('statfs:', req, ino)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def listxattr(self, req, ino, size):
        print('listxattr:', req, ino, size)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def setxattr(self, req, ino, name, value, size, flags):
        print('setxattr:', req, ino, name, value, size, flags)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def getxattr(self, req, ino, name, size):
        print('getxattr:', req, ino, name, size)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def removexattr(self, req, ino, name):
        print('removexattr:', req, ino, name)

        # error because its not implemented
        self.reply_err(req,errno.ENOSYS)

    def symlink(self, req, link, parent, name):
        print('symlink:', req, link, parent, name)
        # error ENOENT to stop process
        self.reply_err(req,errno.EROFS)

# following functions may not be required, but if we have time we can implement
# them for more functionality

##    def opendir(self, req, ino, fi):
##        print('opendir:', req, ino, fi)
##        # error because its not implemented
##        self.reply_err(req,errno.ENOSYS)

##    def releasedir(self, req, ino, fi):
##        print('releasedir:', req, ino, fi)
##        # error because its not implemented
##        self.reply_err(req,errno.ENOSYS)

    def fsync(self, req, ino, datasync, fi):
        """Synchronize file contents

        Valid replies:
            reply_err
        """

        self._log.flush()

##    def fsyncdir(self, req, ino, datasync, fi):
##        print('fsyncdir:', req, ino, datasync, fi)
##        # return no error
##        self.reply_err(req,0)

    def _checkpoint_if_necessary(self):
        current_time = int(time())
        last_checkpoint_time = this._CR.time()

        if (current_time - last_checkpointed_segment_id) >= self.checkpoint_frequency:
            self._save_checkpoint()

    def _save_checkpoint(self):
        current_segment_id = this._log.get_current_segment_id()
        this._CR.set_segment_id(current_segment_id)
        this._CR.set_time(int(time()))
        serialized_checkpoint = this._CR.to_bytes()
        this._bucket.put_checkpoint(serialized_checkpoint)
