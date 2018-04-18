from unittest import TestCase
from unittest.mock import Mock, ANY
from s3logfs.fs import Log, ReadOnlySegment, ReadWriteSegment, BlockAddress


class TestLog(TestCase):
    def test_read_block_from_a_previous_segment_should_return_the_block(self):
        block_size = 64
        address = BlockAddress(123, 1)
        block_bytes = b'abc'
        segment = ReadWriteSegment(123, block_size=block_size)
        segment.write_data(block_size * b'x')
        segment.write_data(block_bytes)
        backend = Mock()
        backend.get_segment.return_value = segment.to_bytes()
        log = Log(999, backend, block_size=block_size)

        result = log.read_block(address)

        self.assertEqual(bytes(result[:len(block_bytes)]), block_bytes)
        backend.get_segment.assert_called_once_with(address.segmentid)

    def test_read_block_from_current_segment_should_return_the_block(self):
        block_size = 64
        address = BlockAddress(123, 2)
        block_bytes = block_size * b'a'
        backend = Mock()
        log = Log(address.segmentid, backend, block_size=block_size)

        for _ in range(address.offset):
            log.write_data_block(block_size * b'x')

        log.write_data_block(block_bytes)
        result = log.read_block(address)

        self.assertEqual(bytes(result), block_bytes)
        backend.get_segment.assert_not_called()

    def test_write_data_block_should_write_to_the_current_segment(self):
        current_segment_id = 123
        backend = Mock()
        log = Log(current_segment_id, backend)
        bytes = b'abc'

        block_address = log.write_data_block(bytes)

        self.assertEqual(block_address.segmentid, current_segment_id)
        self.assertEqual(log.get_current_segment_id(), current_segment_id)
        backend.put_segment.assert_not_called()

    def test_write_inode_should_write_to_the_current_segment(self):
        current_segment_id = 123
        backend = Mock()
        log = Log(current_segment_id, backend)
        bytes = b'abc'

        block_address = log.write_inode(bytes, 123)

        self.assertEqual(block_address.segmentid, current_segment_id)
        self.assertEqual(log.get_current_segment_id(), current_segment_id)
        backend.put_segment.assert_not_called()

    def test_write_data_block_when_segment_is_full_should_put_the_segment(self):
        current_segment_id = 123
        block_size = 128
        blocks_per_segment = 64
        block_bytes = block_size * b'x'
        backend = Mock()
        log = Log(current_segment_id, backend, block_size=block_size,
                  blocks_per_segment=blocks_per_segment)

        for block_number in range(blocks_per_segment):
            block_address = log.write_data_block(block_bytes)
            self.assertEqual(block_address.offset, block_number)

        # test that the current segment id is the starting id + 1
        self.assertEqual(log.get_current_segment_id(), current_segment_id + 1)
        backend.put_segment.assert_called_once_with(current_segment_id, ANY)

    def test_write_inode_when_segment_is_full_should_put_the_segment(self):
        current_segment_id = 123
        block_size = 128
        blocks_per_segment = 64
        block_bytes = block_size * b'x'
        backend = Mock()
        log = Log(current_segment_id, backend, block_size=block_size,
                  blocks_per_segment=blocks_per_segment)

        for block_number in range(blocks_per_segment):
            block_address = log.write_inode(block_bytes, 123)
            self.assertEqual(block_address.offset, block_number)

        # test that the current segment id is the starting id + 1
        self.assertEqual(log.get_current_segment_id(), current_segment_id + 1)
        backend.put_segment.assert_called_once_with(current_segment_id, ANY)

    def test_flush(self):
        current_segment_id = 123
        block_size = 128
        blocks_per_segment = 8
        backend = Mock()
        log = Log(current_segment_id, backend, block_size=block_size,
                  blocks_per_segment=blocks_per_segment)

        block = block_size * b'a'
        for i in range(blocks_per_segment):
            block_address = log.write_data_block(block)

        log.flush()

        self.assertEqual(log.get_current_segment_id(), current_segment_id + 1)
        backend.put_segment.assert_called_once_with(current_segment_id, ANY)
        backend.flush.assert_called_once_with()

    def test_flush_when_segment_empty(self):
        current_segment_id = 123
        backend = Mock()
        log = Log(current_segment_id, backend)

        log.flush()

        self.assertEqual(log.get_current_segment_id(), current_segment_id)
        backend.put_segment.assert_not_called()
        backend.flush.assert_called_once_with()
