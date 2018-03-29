from abc import ABC, abstractmethod


class Segment(ABC):
    '''
    This is an abstract class and should not be instantiated directly.
    Instead, use either ReadOnlySegment or ReadWriteSegment.
    '''

    # Should this be constant?
    BLOCK_SIZE = 512

    def __len__(self):
        return len(self.bytes())

    @abstractmethod
    def bytes(self):
        '''
        This must be implemented by every child class. Making this abstract
        allows different representations of the bytes to be used.
        '''
        raise NotImplementedError

    def read(self, block_number):
        offset = block_number * self.BLOCK_SIZE
        return self.bytes()[offset:offset + self.BLOCK_SIZE]


class ReadOnlySegment(Segment):
    '''
    Since this class is only for reading from a segment we can store the data in
    a memoryview, which allows us to take slices of the data without copying.
    '''

    def __init__(self, bytes):
        self._memoryview = memoryview(bytes)

    def bytes(self):
        return self._memoryview


class ReadWriteSegment(Segment):
    '''
    This class represents a segment which is not yet complete, and so can
    be written to. The data is therefore represented as a bytearray, which is
    mutable. When the segment is complete it should be converted into a
    ReadOnlySegment.
    '''

    def __init__(self):
        self._next_block_number = 0
        self._bytearray = bytearray()

    def bytes(self):
        return self._bytearray

    def to_read_only(self):
        return ReadOnlySegment(self._bytearray)

    def write(self, block_bytes):
        if len(block_bytes) > self.BLOCK_SIZE:
            raise RuntimeError('Segment must be written to one block at a time')

        self._bytearray.extend(block_bytes)
        if len(block_bytes) < self.BLOCK_SIZE:
            padding = (self.BLOCK_SIZE - len(block_bytes)) * [0]
            self._bytearray.extend(padding)

        block_number = self._next_block_number
        self._next_block_number += 1
        return block_number
