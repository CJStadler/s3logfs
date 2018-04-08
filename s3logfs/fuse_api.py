#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

import errno
from datetime import datetime
from stat import *
import math

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
        root_inode.mode = S_IFDIR | 0o777                  # directory with 777 chmod
        root_inode.hard_links = 2                          # "." and ".." make the first 2 hard links

        # 2. write root inode directory data to log
        # -- convert children to bytes
        data = root_inode.children_to_bytes()
        # -- cut bytes up into block_size units and write each unit storing addr to inode
        number_blocks = math.ceil(len(data)/self._log.get_block_size()) 
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


#        test_inode_id = self._CR.root_inode_id
#        test_addr = self._CR.inode_map[test_inode_id]
#        data = self._log.read(test_addr)
#        test = INode()
#        test = test.from_bytes(data)
        # get data for children
#        data = bytearray()
#        for x in range(test.block_count):
#            data.extend(self._log.read(test.read_address()))
#        test.bytes_to_children(bytes(data))


        # might implement the above by defining a directory INode
        # and then writing it to the segment.

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
        for x in range(parent_inode.block_count):
            data.extend(self._log.read(parent_inode.read_address()))
        parent_inode.bytes_to_children(bytes(data))

        # obtain child inodeid via name
        try:
            child_inode_id = parent_inode.children[name]
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
        """Set file attributes

        Valid replies:
            reply_attr
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def mknod(self, req, parent, name, mode, rdev):
        """Create file node

        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def mkdir(self, req, parent, name, mode):
        """Create a directory

        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def unlink(self, req, parent, name):
        """Remove a file

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def rmdir(self, req, parent, name):
        """Remove a directory

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.EROFS)

    def rename(self, req, parent, name, newparent, newname):
        """Rename a file

        Valid replies:
            reply_err
        """
        self.reply_err(req, errno.EROFS)

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
        """Read directory

        Valid replies:
            reply_readdir
            reply_err
        """
        self.reply_err(req, errno.ENOENT)

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
