from abc import ABC
from collections import defaultdict


class Segment(ABC):
    '''
    This is an abstract class and should not be instantiated directly.
    Instead, use either ReadOnlySegment or ReadWriteSegment.
    '''

    def __init__(self, segment_id, block_size, max_block_count):
        self._id = segment_id
        self._block_size = block_size
        self._max_block_count = max_block_count
        self._in_s3 = False

    def __len__(self):
        return len(self._bytes_representation)

    def get_id(self):
        return self._id

    def get_block_size(self):
        return self._block_size

    def get_max_block_count(self):
        return self._max_block_count

    def is_in_s3(self):
        return self._in_s3

    # set S3 status (True/False expected)
    def set_s3(self, status):
        self._in_s3 = status

    # returns if the segment is full only if RW and next block number matches segment size OR Read Only
    def is_full(self):
        return isinstance(self, ReadOnlySegment) or self._next_block_number >= self._max_block_count

    def bytes(self):
        return bytes(self._bytes_representation)

    def read_block(self, block_number):
        '''
        Returns the requested block as a bytes-like object.

        Precondition: block_number < the number of blocks in self
        '''
        offset = block_number * self._block_size
        return self._bytes_representation[offset:offset + self._block_size]


class ReadOnlySegment(Segment):
    '''
    Since this class is only for reading from a segment we can store the data in
    a memoryview, which allows us to take slices of the data without copying.
    '''

    def __init__(self, bytes, segment_id, block_size=4096, max_block_count=512):
        super().__init__(segment_id, block_size, max_block_count)
        self._bytes_representation = memoryview(bytes)


class ReadWriteSegment(Segment):
    '''
    This class represents a segment which is not yet complete, and so can
    be written to. The data is therefore represented as a bytearray, which is
    mutable. When the segment is complete it should be converted into a
    ReadOnlySegment.
    '''

    def __init__(self, segment_id, block_size=4096, max_block_count=512):
        super().__init__(segment_id, block_size, max_block_count)
        self._bytes_representation = bytearray()
        self._next_block_number = 0

    def to_read_only(self):
        # i think we should pad the segment to zero's if we force the segment to write early
        return ReadOnlySegment(self._bytes_representation, self._id, self._block_size, self._max_block_count)

    def write(self, block_bytes):
        '''
        Adds the given block to the segment. The block will be padded with 0 if
        it is not equal to block_size.

        Returns the number of the block.

        Precondition: len(block_bytes) <= block_size
        Precondition: Segment is not full
        '''

        self._bytes_representation.extend(block_bytes)

        if len(block_bytes) < self._block_size:
            padding = (self._block_size - len(block_bytes)) * b'0'
            self._bytes_representation.extend(padding)

        block_number = self._next_block_number
        self._next_block_number += 1
        return block_number
