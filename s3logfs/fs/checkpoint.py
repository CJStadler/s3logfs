import struct
from . import BlockAddress
from collections import defaultdict
import pickle

class CheckpointRegion:

    def __init__(self, bucket="TEST", start_inode=0, block_size=4096, blocks_per_segment=512):
        self.block_size = block_size             # bytes
        self.segment_size = blocks_per_segment   # blocks (default 2MB)
        self.fs_size = 2**28                     # blocks (default 1TB space)
        self.fs_used = 0                         # blocks
        self._segment_counter = 0                # unsigned long long
        self._inode_counter = startINode         # unsigned long long
        self.s3_bucket_name = bucket             # s3 bucket name
        self.inode_map = defaultdict()           # inodeid <> BlockAddress

    def from_bytes(serialized_checkpoint):
        return pickle.loads(serialized_checkpoint)

    # returns the next inodeid
    def next_inode_id(self):
        self._inode_counter += 1
        return self._inode_counter

    # returns the next segmentid
    def next_segment_id(self):
        self._segment_counter += 1
        return self._segment_counter

    def current_segment_id(self):
        return self._segment_counter

    def to_bytes(self):
        return pickle.dumps(self)
 
    # check if inode exists
    def inode_exists(self, inode_number):
        if inode_number in self.inode_map:
            return True
        else:
            return False