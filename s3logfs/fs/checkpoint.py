import struct
from blockaddress import BlockAddress
from collections import defaultdict
import pickle

class CheckpointRegion:

  def __init__(self):
    self.blockSize = 4096          # bytes
    self.segmentSize = 512         # blocks
    self.fsSize = 2**15            # blocks
    self.fsUsed = 0                # blocks
    self.segmentCounter = 0        # unsigned long long (limited to 6 bytes)
    self.iNodeCounter = 0          # unsigned long long
    self.iNodeMap = defaultdict()


