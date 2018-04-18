from collections import defaultdict
from .segment import ReadOnlySegment, ReadWriteSegment
from .blockaddress import BlockAddress


class Log:
    """
    Abstract representation of the log.

    Only a single instance of this class should exist for a filesystem at one
    time.
    """

    def __init__(self, current_segment_id, backend, block_size=4096, blocks_per_segment=512):
        self._current_segment_id = current_segment_id
        self._backend = backend
        self._block_size = block_size
        self._blocks_per_segment = blocks_per_segment
        self._current_segment = ReadWriteSegment(
            current_segment_id,
            block_size=block_size,
            max_block_count=blocks_per_segment
        )

    def get_current_segment_id(self):
        return self._current_segment_id

    def get_block_size(self):
        return self._block_size

    def read_block(self, block_address):
        '''
        Returns the block (as a memoryview) at the given block_address.

        Precondition: block_address.segmentid <= current_segment_id
        '''
        if block_address.segmentid == self._current_segment_id:
            segment = self._current_segment
        else:
            segment_bytes = self._backend.get_segment(block_address.segmentid)
            segment = ReadOnlySegment(
                segment_bytes,
                block_address.segmentid,
                block_size=self._block_size,
                max_block_count=self._blocks_per_segment,
            )

        return segment.read_block(block_address.offset)

    def write_data_block(self, block_bytes):
        '''
        Writes the given bytes to the current segment. If this fills the segment
        then the segment is sent to the backend.

        Precondition: len(block_bytes) <= block_size
        '''
        block_number = self._current_segment.write_data(block_bytes)
        segment_number = self._current_segment_id

        if self._current_segment.is_full():
            self._put_current_segment()

        return BlockAddress(segment_number, block_number)

    def write_inode(self, inode_bytes, inode_number):
        '''
        Writes the serialized inode to the current segment. If this fills the segment
        then the segment is sent to the backend.

        Precondition: len(inode_bytes) <= block_size
        '''
        block_number = self._current_segment.write_inode(
            inode_bytes, inode_number)
        segment_number = self._current_segment_id

        if self._current_segment.is_full():
            self._put_current_segment()

        return BlockAddress(segment_number, block_number)

    def flush(self):
        if len(self._current_segment) > 0:
            self._put_current_segment()

        self._backend.flush()

    def _put_current_segment(self):
        self._backend.put_segment(
            self._current_segment_id,
            self._current_segment.to_bytes()
        )

        self._current_segment_id += 1
        self._current_segment = ReadWriteSegment(
            self._current_segment_id,
            block_size=self._block_size,
            max_block_count=self._blocks_per_segment
        )
