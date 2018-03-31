import struct
from blockaddress import BlockAddress
from collections import defaultdict

class CheckpointRegion:

  def __init__(self):
    self.blockSize = 4096          # bytes
    self.segmentSize = 512         # blocks (default 2MB)
    self.fsSize = 2**28            # blocks (default 1TB space)
    self.fsUsed = 0                # blocks
    self.segmentCounter = 0        # unsigned long long (limited to 6 bytes)
    self.iNodeCounter = 0          # unsigned long long
    self.iNodeMap = defaultdict()  # inodeid <> BlockAddress of iNode in log


