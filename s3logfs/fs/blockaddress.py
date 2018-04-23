import struct

# combined these make a single address
ADDR_SEGMENT_BYTES = 6
ADDR_OFFSET_BYTES = 2

class BlockAddress:
    STRUCT_SIZE = 8

    # BlockAddress constructor accepts either ...
    #  - bytearray (1 argument)
    #  - segmentid,offset (2 arguments)
    def __init__(self, *args, **kwargs):
        if (len(args) == 0): # empty (set to 0,0)
            # base address (0,0)
            self.segmentid = 0
            self.offset = 0
        elif (len(args) == 1):  # bytearray
            # first x bytes is segmentid (placed in unsigned long long)
            self.segmentid = struct.unpack("<Q", bytes(args[0][0:ADDR_SEGMENT_BYTES]) + b'\x00\x00')[0]
            # last y bytes is offset (placed in unsigned short)
            self.offset = struct.unpack("<H", args[0][ADDR_SEGMENT_BYTES:ADDR_SEGMENT_BYTES+ADDR_OFFSET_BYTES])[0]
        elif (len(args) == 2):  # segmentid & offset
            # first argument is segmentid
            self.segmentid = args[0]
            # 2nd argument is offset
            self.offset = args[1]
        # invalid number of arguments
        else:
            # *** need to replace this with how we will handle errors ***
            return NotImplemented

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return (self.segmentid == other.segmentid and self.offset == other.offset)
        return NotImplemented

    def __hash__(self):
        return hash((self.segmentid, self.offset))

    def __str__(self):
        return "BlockAddress(" + str(self.segmentid) + "," + str(self.offset) + ")"

    # returns BlockAddress as a list of bytes
    def to_bytes(self):
        b1 = (self.segmentid).to_bytes(ADDR_SEGMENT_BYTES, byteorder='little', signed=False)
        b2 = (self.offset).to_bytes(ADDR_OFFSET_BYTES, byteorder='little', signed=False)
        return b1[0:ADDR_SEGMENT_BYTES] + b2[0:ADDR_OFFSET_BYTES]

    # set's a block address from bytes
    def from_bytes(self, data):
            # first X bytes is segmentid (placed in unsigned long long)
        self.segmentid = struct.unpack("<Q", data[0:ADDR_SEGMENT_BYTES] + b'\x00\x00')[0]
        # last Y bytes is offset (placed in unsigned short)
        self.offset = struct.unpack("<H", data[ADDR_SEGMENT_BYTES:ADDR_SEGMENT_BYTES+ADDR_OFFSET_BYTES])[0]

    # returns the number of blocks for a address in the log
    def get_address_size():
        return ADDR_SEGMENT_BYTES+ADDR_OFFSET_BYTES
