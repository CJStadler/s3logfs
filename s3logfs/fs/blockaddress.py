class BlockAddress:

  # BlockAddress constructor accepts either ...
  #  - bytearray (1 argument)
  #  - segmentid,offset (2 arguments)
  def __init__(self, *args, **kwargs):
    # 10-byte bytearray (8 = segmentid, 2 = offset)
    if (len(args) == 1):  # bytearray
      # first 8 bytes is segmentid
      self.segmentid = struct.unpack("<Q", args[0][0:8])[0]
      # last 2 bytes is offset
      self.offset = struct.unpack("<H", args[0][8:10])[0]
    elif (len(args) == 2):  # segmentid & offset
      # first argument is segmentid
      self.segmentid = args[0]
      # 2nd argument is offset
      self.offset = args[1]
    # invalid number of arguments
    else:
      # *** need to replace this with how we will handle errors ***
      print("ERROR")
  
  # returns BlockAddress as a list of 10 bytes
  def to_bytes(self):
    b1 = (self.segmentid).to_bytes(8, byteorder='little', signed=False)
    b2 = (self.offset).to_bytes(2, byteorder='little', signed=False)
    return b1[0:8] + b2[0:2]
