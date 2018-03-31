import struct
from blockaddress import BlockAddress
from collections import defaultdict

class CheckpointRegion:
  def __init__(self):
    self.iNodeMap = defaultdict()
