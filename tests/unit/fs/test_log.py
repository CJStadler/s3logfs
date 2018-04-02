from unittest import TestCase
from unittest.mock import Mock
from s3logfs.fs import Log, ReadOnlySegment, ReadWriteSegment, BlockAddress


class TestLog(TestCase):
    def test_read_from_previous_segment(self):
        segment_size = 4096
        last_segment_number = 123
        segment_number = 123
        bucket = Mock()
        log = Log(segment_size, last_segment_number, bucket)
        block_number = 7
        seg_bytes = bytearray(segment_size)
        block = ReadOnlySegment.BLOCK_SIZE * b'a'
        offset = block_number * ReadOnlySegment.BLOCK_SIZE
        seg_bytes[offset:offset + ReadOnlySegment.BLOCK_SIZE] = block
        bucket.get_segment.return_value = bytes(seg_bytes)
        result = log.read(BlockAddress(segment_number, block_number))
        self.assertEqual(result, block)
        bucket.get_segment.assert_called_once_with(segment_number)

    def test_read_from_current_segment(self):
        segment_size = 4096
        last_segment_number = 123
        bucket = Mock()
        log = Log(segment_size, last_segment_number, bucket)
        block = ReadOnlySegment.BLOCK_SIZE * b'a'
        address = log.write(block)
        result = log.read(address)
        self.assertEqual(result, block)

    def test_write_when_segment_not_complete(self):
        last_segment_number = 123
        bucket = Mock()
        log = Log(4096, last_segment_number, bucket)
        bytes = b'abc'
        block_address = log.write(bytes)
        self.assertEqual(block_address, BlockAddress(last_segment_number + 1, 0))
        self.assertEqual(log.last_segment_number, last_segment_number)

    def test_write_when_segment_complete(self):
        segment_size = 4096
        last_segment_number = 123
        bucket = Mock()
        log = Log(segment_size, last_segment_number, bucket)
        block = ReadWriteSegment.BLOCK_SIZE * b'a'
        blocks_count = segment_size // ReadWriteSegment.BLOCK_SIZE
        for i in range(blocks_count):
            block_address = log.write(block)

        self.assertEqual(block_address,
                         BlockAddress(last_segment_number + 1, blocks_count - 1))
        self.assertEqual(log.last_segment_number, last_segment_number + 1)
        bucket.put_segment.assert_called_once_with(
            last_segment_number + 1,
            blocks_count * block
        )
