from abc import ABC, abstractmethod
from collections import defaultdict

class Segment(ABC):
    '''
    This is an abstract class and should not be instantiated directly.
    Instead, use either ReadOnlySegment or ReadWriteSegment.
    '''

    def __len__(self):
        return len(self.bytes())

    def get_id(self):
        return self._id

    def get_type(self):
        return self._type

    def get_block_size(self):
        return self._block_size

    def is_in_s3(self):
        return self._in_s3

    # set S3 status (True/False expected)
    def set_s3(self, status):
        self._in_s3 = status

    # returns if the segment is full only if RW and next block number mathces segment size OR Read Only
    def is_full(self):
        if (self._type == "RO"):
            return True
        elif (self._next_block_number == self._segment_size-1):
            return True
        else:
            return False

    @abstractmethod
    def bytes(self):
        '''
        This must be implemented by every child class. Making this abstract
        allows different representations of the bytes to be used.
        '''
        raise NotImplementedError

    @abstractmethod
    def read(self, block_number):
        '''
        This must be implemented by every child class. Making this abstract
        allows different representations of the bytes to be used.
        '''
        raise NotImplementedError

class ReadOnlySegment(Segment):
    '''
    Since this class is only for reading from a segment we can store the data in
    a memoryview, which allows us to take slices of the data without copying.
    '''

    def __init__(self, bytes=b'', segment_id=0, block_size=4096, segment_size=512):
        self._id = segment_id 
        self._type = "RO"
        self._block_size = block_size
        self._segment_size = segment_size
        self._memoryview = memoryview(bytes)
        self._in_s3 = False

    def bytes(self):
        return bytes(self._memoryview)

    def read(self, block_number):
        offset = block_number * self._block_size
        return self._memoryview[offset:offset + self._block_size].tobytes()


class ReadWriteSegment(Segment):
    '''
    This class represents a segment which is not yet complete, and so can
    be written to. The data is therefore represented as a bytearray, which is
    mutable. When the segment is complete it should be converted into a
    ReadOnlySegment.
    '''

    def __init__(self, segment_id=0, block_size=4096, segment_size=512):
        self._id = segment_id
        self._type = "RW"
        self._block_size = block_size
        self._segment_size = segment_size
        self._next_block_number = 0
        self._bytearray = bytearray()
        self._in_s3 = False

    def bytes(self):
        return bytes(self._bytearray)

    def to_read_only(self):
        # i think we should pad the segment to zero's if we force the segment to write early
        return ReadOnlySegment(self.bytes(), self._id, self._block_size, self._segment_size)

    def write(self, block_bytes):
        if len(block_bytes) > self._block_size:
            raise RuntimeError('Segment must be written to one block at a time')

        self._bytearray.extend(block_bytes)

        if len(block_bytes) < self._block_size:
            padding = (self._block_size - len(block_bytes)) * [0]
            self._bytearray.extend(padding)

        block_number = self._next_block_number
        self._next_block_number += 1
        return block_number

    def read(self, block_number):
        offset = block_number * self._block_size
        return bytes(self._bytearray[offset:offset + self._block_size])


