import errno
from datetime import datetime

from .fs import CheckpointRegion
from .s3_bucket import S3Bucket
from .fs import Log
from .fs import INode
from .fs import BlockAddress

from .fusell import FUSELL


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

        # init superblock
        
        # init CheckpointRegion - new FS, no recovery yet
        self._CR = CheckpointRegion(self._bucket_name, 0)

        # store superblock in CheckpointRegion

        # init S3 bucket
        self._bucket = S3Bucket(self._bucket_name);

        # init Log
        self._log = Log(self._CR.nextSegmentId(), self._bucket, self.CR.block_size, self.CR.segment_size)

        # need to init default root structure in files
        # 1. empty directory data block
        # 2. directory inode block
        # 3. update self._CR inode_map with inodeid to BlockAddress in log 

        # might implement the above by defining a directory INode
        # and then writing it to the segment.

    def destroy(self, userdata):
        """Clean up filesystem

        There's no reply to this method
        """
        pass

    def lookup(self, req, parent, name):
        """Look up a directory entry by name and get its attributes.

        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, errno.ENOENT)

    def forget(self, req, ino, nlookup):
        """Forget about an inode

        Valid replies:
            reply_none
        """
        self.reply_none(req)

    def getattr(self, req, ino, fi):
        """Get file attributes

        Valid replies:
            reply_attr
            reply_err
        """
        self.reply_err(req, errno.ENOENT)

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
