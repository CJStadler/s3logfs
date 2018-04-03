from unittest import TestCase
import os
from unittest.mock import Mock
from s3logfs.fs import Log, ReadOnlySegment, ReadWriteSegment, BlockAddress


class TestLog(TestCase):
    def test_read_from_previous_segment(self):
        # setup test requirements
        segment_size = 512
        last_segment_number = 123
        savedAddress = BlockAddress(0,0)
        bucket = Mock()
        log = Log(last_segment_number, bucket, ReadOnlySegment.BLOCK_SIZE, segment_size)
        # write several segments worth of random data, saving first address and block
        for x in range(1, segment_size*3):
          seg_bytes = bytearray(segment_size)
          block = bytes(os.urandom(ReadOnlySegment.BLOCK_SIZE))
          addr = log.write(block)
          if (x==1):
            savedAddress = addr
            savedBlock = block
        # using saved address read what should be the saved block
        result = log.read(savedAddress)
        # compare
        self.assertEqual(result, savedBlock)

    def test_read_from_current_segment(self):
        segment_size = 512
        last_segment_number = 123
        bucket = Mock()
        log = Log(last_segment_number, bucket, ReadOnlySegment.BLOCK_SIZE, segment_size)
        block = ReadOnlySegment.BLOCK_SIZE * b'a'
        address = log.write(block)
        result = log.read(address)
        self.assertEqual(result, block)

    def test_write_when_segment_not_complete(self):
        last_segment_number = 123
        segment_size = 512
        bucket = Mock()
        log = Log(last_segment_number, bucket, ReadOnlySegment.BLOCK_SIZE, segment_size)
        bytes = b'abc'
        block_address = log.write(bytes)
        self.assertEqual(str(block_address.segmentid)+" "+str(block_address.offset), "123 0")
        self.assertEqual(log.getCurrentSegment(), last_segment_number)

    def test_write_when_segment_complete(self):
        segment_size = 512
        last_segment_number = 123
        bucket = Mock()
        log = Log(last_segment_number, bucket, ReadOnlySegment.BLOCK_SIZE, segment_size)
        block = ReadWriteSegment.BLOCK_SIZE * b'a'
        blocks_count = segment_size // ReadWriteSegment.BLOCK_SIZE
        for i in range(blocks_count):
            block_address = log.write(block)

            self.assertEqual(block_address,
                             BlockAddress(last_segment_number + 1, blocks_count - 1))
            self.assertEqual(log.last_segment_number, last_segment_number + 1)
            #bucket.put_segment.assert_called_once_with(
            #                 last_segment_number + 1,
            #                 blocks_count * block
            #                 )
