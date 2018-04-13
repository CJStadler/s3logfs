import struct
from . import BlockAddress
from collections import defaultdict

class CheckpointRegion:

  def __init__(self, bucket="TEST", start_inode=0):
    self.root_inode_id = 0
    self.block_size = 4096           # bytes
    self.segment_size = 512          # blocks (default 2MB)
    self.fs_size = 2**28             # blocks (default 1TB space)
    self.fs_used = 0                 # blocks
    self._segment_counter = 0        # unsigned long long
    self._inode_counter = start_inode # unsigned long long
    self.s3_bucket_name = bucket     # s3 bucket name
    self.inode_map = defaultdict()   # inodeid <> BlockAddress

  # returns the next inodeid
  def next_inode_id(self):
    self._inode_counter += 1
    return self._inode_counter

  # returns the next segmentid
  def next_segment_id(self):
    self._segment_counter += 1
    return self._segment_counter

  # check if inode exists
  def inode_exists(self, inode_number):
    if inode_number in self.inode_map:
      return True
    else:
      return False

