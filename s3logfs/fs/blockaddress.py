import struct


class BlockAddress:

    # BlockAddress constructor accepts either ...
    #  - bytearray (1 argument)
    #  - segmentid,offset (2 arguments)
    def __init__(self, *args, **kwargs):
        if (len(args) == 0): # empty (set to 0,0)
            # base address (0,0)
            self.segmentid = 0
            self.offset = 0
        elif (len(args) == 1):  # bytearray
            # first 6 bytes is segmentid (placed in unsigned long long)
            self.segmentid = struct.unpack("<Q", bytes(args[0][0:6]) + b'\x00\x00')[0]
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
            return NotImplemented

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return (self.segmentid == other.segmentid and self.offset == other.offset)
        return NotImplemented

    def __hash__(self):
        return hash((self.segmentid, self.offset))

    # returns BlockAddress as a list of 8 bytes
    def to_bytes(self):
        b1 = (self.segmentid).to_bytes(6, byteorder='little', signed=False)
        b2 = (self.offset).to_bytes(2, byteorder='little', signed=False)
        return b1[0:6] + b2[0:2]

    # set's a block address from bytes
    def from_bytes(self, data):
            # first 6 bytes is segmentid (placed in unsigned long long)
        self.segmentid = struct.unpack("<Q", data[0:6] + b'\x00\x00')[0]
        # last 2 bytes is offset (placed in unsigned short)
        self.offset = struct.unpack("<H", data[6:8])[0]
