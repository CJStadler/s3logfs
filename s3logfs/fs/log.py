from .segment import ReadOnlySegment, ReadWriteSegment
from .blockaddress import BlockAddress

class Log:
    """
    Abstract representation of the log.

    Only a single instance of this class should exist for a filesystem at one
    time.
    """

    def __init__(self, max_segment_size, last_segment_number, bucket):
        self._max_segment_size = max_segment_size
        self.last_segment_number = last_segment_number # Not including current segment
        self._bucket = bucket
        self._current_segment = ReadWriteSegment()

    def read(self, block_address):
        if block_address.segmentid == self.last_segment_number + 1:
            segment = self._current_segment
        else:
            seg_bytes = self._bucket.get_segment(block_address.segmentid)
            segment = ReadOnlySegment(seg_bytes)

        return segment.read(block_address.offset)

    def write(self, block_bytes):
        block_number = self._current_segment.write(block_bytes)
        segment_number = self.last_segment_number + 1

        if len(self._current_segment) > self._max_segment_size:
            raise RuntimeError('Segment length is greater than max size')
        elif len(self._current_segment) == self._max_segment_size:
            self._put_current_segment()

        return BlockAddress(segment_number, block_number)

    def _put_current_segment(self):
        self.last_segment_number += 1
        self._bucket.put_segment(
            self.last_segment_number,
            bytes(self._current_segment.bytes()) # bytearray -> bytes
        )
        self._current_segment = ReadWriteSegment()
