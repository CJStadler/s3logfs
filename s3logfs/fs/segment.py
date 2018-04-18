from abc import ABC
from collections import defaultdict
from pickle import dumps, loads

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
        return len(self._block_bytes)

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

    def to_bytes(self):
        summary_bytes = dumps(self._inode_block_numbers)

        if len(summary_bytes) < self._block_size:
            padding = (self._block_size - len(summary_bytes)) * b'\0'
            summary_bytes += padding

        return summary_bytes + self._block_bytes

    def read_block(self, block_number):
        '''
        Returns the requested block as a bytes-like object.

        Precondition: block_number < the number of blocks in self
        '''
        offset = block_number * self._block_size
        return self._block_bytes[offset:offset + self._block_size]

    def inode_block_numbers(self):
        return self._inode_block_numbers


class ReadOnlySegment(Segment):
    '''
    Since this class is only for reading from a segment we can store the data in
    a memoryview, which allows us to take slices of the data without copying.
    '''

    def __init__(self, bytes, segment_id, block_size=4096, max_block_count=512):
        super().__init__(segment_id, block_size, max_block_count)
        memview = memoryview(bytes)
        self._block_bytes = memview[block_size:]
        summary_bytes = memview[:block_size]
        self._inode_block_numbers = loads(summary_bytes)


class ReadWriteSegment(Segment):
    '''
    This class represents a segment which is not yet complete, and so can
    be written to. The data is therefore represented as a bytearray, which is
    mutable.
    '''

    def __init__(self, segment_id, block_size=4096, max_block_count=512):
        super().__init__(segment_id, block_size, max_block_count)
        self._block_bytes = bytearray()
        self._next_block_number = 0
        self._inode_block_numbers = [] # (inode number, block number)

    def to_read_only(self):
        return ReadOnlySegment(self.to_bytes(), self._id, self._block_size, self._max_block_count)

    def write_inode(self, block_bytes, inode_number):
        block_number = self._write_block(block_bytes)
        self._inode_block_numbers.append((inode_number, block_number))
        return block_number

    def write_data(self, block_bytes):
        return self._write_block(block_bytes)

    def _write_block(self, block_bytes):
        '''
        Adds the given block to the segment. The block will be padded with 0 if
        it is not equal to block_size.

        Returns the number of the block.

        Precondition: len(block_bytes) <= block_size
        Precondition: Segment is not full
        '''

        self._block_bytes.extend(block_bytes)

        if len(block_bytes) < self._block_size:
            padding = (self._block_size - len(block_bytes)) * b'\0'
            self._block_bytes.extend(padding)

        block_number = self._next_block_number
        self._next_block_number += 1
        return block_number
