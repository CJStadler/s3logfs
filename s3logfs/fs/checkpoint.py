import struct
from . import BlockAddress
from collections import defaultdict

class CheckpointRegion:

  def __init__(self, bucket="TEST", startINode=0):
    self.block_size = 4096           # bytes
    self.segment_size = 512          # blocks (default 2MB)
    self.fs_size = 2**28             # blocks (default 1TB space)
    self.fs_used = 0                 # blocks
    self._segment_counter = 0        # unsigned long long
    self._inode_counter = 0          # unsigned long long
    self.s3_bucket_name = bucket     # s3 bucket name
    self.inode_map = defaultdict()   # inodeid <> BlockAddress

  # returns the next inodeid
  def nextINode():
    inodeid = self._inode_counter
    self._inode_counter += 1
    return inodeid

  # returns the next segmentid
  def nextSegmentId():
    segid = self._segment_counter
    self._segment_counter += 1
    return segid

