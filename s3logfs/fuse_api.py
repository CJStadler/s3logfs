#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

import errno
from datetime import datetime
from stat import *
import math
from time import time

from .fs import CheckpointRegion
from .s3_bucket import S3Bucket
from .fs import Log
from .fs import INode
from .fs import BlockAddress

from .fusell import FUSELL
from errno import ENOENT


class FuseApi(FUSELL):
    def __init__(self, mountpoint, bucket_name, encoding='utf-8'):
        '''
        This overrides the FUSELL __init__() so that we can set the bucket.
        '''

        # mount point
        self._mount = mountpoint

        # for testing, if "TEST" is passed as the bucket name
        # a new bucket will be created with the current 
        # datetime as the bucket name, otherwise it will be 
        # named with what is passed as an argument
        if (bucket_name == "TEST"):
          self._bucket_name = datetime.now()
          print("DT: ", str(self._bucket_name))
        else:
          self._bucket_name = bucket_name        

        super().__init__(mountpoint, encoding=encoding)

    def init(self, userdata, conn):
        print("FS:INIT")

        # init superblock
        
        # init CheckpointRegion - new FS, no recovery yet
        self._CR = CheckpointRegion(self._bucket_name, 0)

        # store superblock in CheckpointRegion

        # init S3 bucket
        self._bucket = S3Bucket(self._bucket_name);

        # init Log
        self._log = Log(self._CR.next_segment_id(), self._bucket, self._CR.block_size, self._CR.segment_size)

        # need to init empty file system
        # 1. create root inode
        root_inode = INode()
        root_inode.inode_number = self._CR.next_inode_id()
        root_inode.parent = root_inode.inode_number        
        root_inode.mode = S_IFDIR | 0o777                  # directory with 777 chmod
        root_inode.hard_links = 2                          # "." and ".." make the first 2 hard links

        # 2. write root inode directory data to log
        # -- convert children to bytes
        data = root_inode.children_to_bytes()
        # -- cut bytes up into block_size units and write each unit storing addr to inode
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        root_inode.size = number_blocks * self._log.get_block_size()
        print("ROOT SIZE", root_inode.size)
        root_inode.block_count = int(root_inode.size / 512)
        root_inode.block_size = self._log.get_block_size()
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write(block)
            root_inode.write_address(address)

        # 3. write root inode to log
        root_inode_addr = self._log.write(root_inode.to_bytes())
        # 4. update CR inode_map to for "/"
        self._CR.inode_map[root_inode.inode_number] = root_inode_addr
        # 5. update CR root_inode_id for "/"
        self._CR.root_inode_id = root_inode.inode_number

    def destroy(self, userdata):
        """Clean up filesystem

        There's no reply to this method
        """
        pass

    def lookup(self, req, parent, name):
        print("FS:lookup", parent, name)

        # get parent addresses from CR inode_map
        # NOTE: need to determine if ENONET is correct
        parent_address = self._CR.inode_map[parent]

        # load parent inode object
        parent_inode = INode()
        parent_inode = parent_inode.from_bytes(self._log.read(parent_address))
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            addr = parent_inode.read_address(x)
            data.extend(self._log.read(addr))
        parent_inode.bytes_to_children(bytes(data))

        # obtain child inodeid via name, if this fails, it should return an empty dict()
        try:
            child_inode_id = int(parent_inode.children[name])
            # obtain child address
            child_address = self._CR.inode_map[child_inode_id]
            # load child inode
            child_inode = INode()
            child_inode = child_inode.from_bytes(self._log.read(child_address))
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
            self.reply_err(req, ENOENT)

    def forget(self, req, ino, nlookup):
        """Forget about an inode

        Valid replies:
            reply_none
        """
        self.reply_none(req)

    def getattr(self, req, ino, fi):
        print("FS:getattr", ino)

        # LOAD INODE FROM STORAGE
        inode_address = self._CR.inode_map[ino]
        inode = INode()
        inode = inode.from_bytes(self._log.read(inode_address))
        
        # obtain attr object from inode instance
        attr = inode.get_attr()

        # RETURN ATTR OBJECT
        if attr:
            self.reply_attr(req, attr, 1.0)
        else:
            self.reply_err(req, ENOENT)

    def setattr(self, req, ino, attr, to_set, fi):
        print('setattr:', ino, to_set)

        # LOAD INODE FROM STORAGE
        inode_address = self._CR.inode_map[ino]
        inode = INode()
        inode = inode.from_bytes(self._log.read(inode_address))
        
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

            # write modified INODE to storage
            inode_addr = self._log.write(inode.to_bytes())

            # update CR inode_map address
            self._CR.inode_map[inode.inode_number] = inode_addr

            # get modified attr object
            inode_attr = inode.get_attr()

            # return reply_attr wtih modified inode_attr
            self.reply_attr(req, inode_attr, 1.0)
        else:
            self.reply_err(req, ENOENT)

    def mknod(self, req, parent, name, mode, rdev):
        """Create file node

        Valid replies:
            reply_entry
            reply_err
        """
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
        parent_address = self._CR.inode_map[parent]
        parent_inode = INode()
        parent_inode = parent_inode.from_bytes(self._log.read(parent_address))
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read(parent_inode.read_address(x)))
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
            address = self._log.write(block)
            newdir.write_address(address,x)
        # - write newdir inode to log
        newdir_inode_addr = self._log.write(newdir.to_bytes()) 
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
            address = self._log.write(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write(parent_inode.to_bytes())   
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr

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
        """Remove a file

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def rmdir(self, req, parent, name):

        # 1. LOAD PARENT INODE
        # - load inode
        parent_address = self._CR.inode_map[parent]
        parent_inode = INode()
        parent_inode = parent_inode.from_bytes(self._log.read(parent_address))
        data = bytearray()
        for x in range(int(parent_inode.size / parent_inode.block_size)):
            data.extend(self._log.read(parent_inode.read_address(x)))
        parent_inode.bytes_to_children(bytes(data))

        # remove directory from parents children
        parent_inode.children.pop(name)

        # decrement parent hard_links
        parent_inode.hard_links -= 1

        # write parent data
        data = parent_inode.children_to_bytes()
        number_blocks = math.ceil(len(data)/self._log.get_block_size())
        parent_inode.size = number_blocks * self._log.get_block_size()
        parent_inode.block_count = int(parent_inode.size / 512)
        for x in range(number_blocks):
            block = data[x*self._log.get_block_size():(x+1)*self._log.get_block_size()]
            address = self._log.write(block)
            parent_inode.write_address(address, x)
        # - write parent inode to log
        parent_inode_addr = self._log.write(parent_inode.to_bytes())   
        # - update CR inode_map for parent
        self._CR.inode_map[parent_inode.inode_number] = parent_inode_addr

        # return no error
        self.reply_err(req, 0)

    def rename(self, req, parent, name, newparent, newname):
        """Rename a file

        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)

    def link(self, req, ino, newparent, newname):
        """Create a hard link

        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def open(self, req, ino, fi):
        """Open a file

        Valid replies:
            reply_open
            reply_err
        """
        self.reply_err(req, errno.EIO)

    def read(self, req, ino, size, off, fi):
        """Read data

        Valid replies:
            reply_buf
            reply_err
        """
        self.reply_err(req, errno.EIO)

    def write(self, req, ino, buf, off, fi):
        """Write data

        Valid replies:
            reply_write
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def readdir(self, req, ino, size, off, fi):
        print('readdir:', ino)

        # 1. LOAD DIRECTORY INODE
        directory_address = self._CR.inode_map[ino]
        directory = INode()
        directory = directory.from_bytes(self._log.read(directory_address))
        data = bytearray()
        number_blocks = int(directory.size / directory.block_size) 
        for x in range(number_blocks):
            data.extend(self._log.read(directory.read_address(x)))
        directory.bytes_to_children(bytes(data))

        # 2. BUILD DEFUALT LIST OF ENTRIES  
        entries = [
            ('.', {'st_ino': directory.inode_number, 'st_mode': S_IFDIR}),
            ('..', {'st_ino': directory.parent, 'st_mode': S_IFDIR})]

        # 3. ADD CHILDREN TO LIST
        for k,v in directory.children.items():
            # get child address
            child_name = k
            child_addr = self._CR.inode_map[int(v)]
            # load child node
            child_inode = INode()
            child_inode = child_inode.from_bytes(self._log.read(child_addr))
            # set attr object
            child_attr = child_inode.get_attr()
            # add inode/attr to entries
            entries.append((child_name,child_attr))

        self.reply_readdir(req, size, off, entries)

    def access(self, req, ino, mask):
        """Check file access permissions

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.ENOSYS)

    def create(self, req, parent, name, mode, fi):
        """Create and open a file

        Valid replies:
            reply_create
            reply_err
        """
        self.reply_err(req, errno.ENOSYS)
