class BlockAddress:

  # BlockAddress constructor accepts either ...
  #  - bytearray (1 argument)
  #  - segmentid,offset (2 arguments)
  def __init__(self, *args, **kwargs):
    # 8-byte bytearray (6 = segmentid, 2 = offset)
    if (len(args) == 1):  # bytearray
      # first 6 bytes is segmentid (placed in unsigned long long)
      self.segmentid = struct.unpack("<Q", args[0][0:6] + b'\x00\x00')[0]
      # last 2 bytes is offset (placed in unsigned short)
      self.offset = struct.unpack("<H", args[0][6:8])[0]
    elif (len(args) == 2):  # segmentid & offset
      # first argument is segmentid
      self.segmentid = args[0]
      # 2nd argument is offset
      self.offset = args[1]
    # invalid number of arguments
    else:
      # *** need to replace this with how we will handle errors ***
      print("ERROR")
  
  # returns BlockAddress as a list of 8 bytes
  def to_bytes(self):
    b1 = (self.segmentid).to_bytes(6, byteorder='little', signed=False)
    b2 = (self.offset).to_bytes(2, byteorder='little', signed=False)
    return b1[0:6] + b2[0:2]
