from unittest import TestCase
from s3logfs.fs import ReadOnlySegment, ReadWriteSegment


class TestReadOnlySegment(TestCase):
    def test_to_and_from_bytes(self):
        block_size = 64
        block = b'a' * block_size
        rw_segment = ReadWriteSegment(123, block_size=block_size)
        block_number = rw_segment.write_data(block)
        r_segment = rw_segment.to_read_only()

        serialized = r_segment.to_bytes()
        deserialized = ReadOnlySegment(serialized, 123, block_size=block_size)

        self.assertEqual(deserialized.read_block(block_number)[:len(block)], block)

    def test_is_full_should_always_be_true(self):
        segment = ReadWriteSegment(123).to_read_only()

        self.assertTrue(segment.is_full())

    def test_read_block_should_return_the_block(self):
        block_size = 64
        block0 = b'x' * block_size
        block1 = b'a' * block_size
        rw_segment = ReadWriteSegment(123, block_size=block_size)
        rw_segment.write_data(block0)
        rw_segment.write_data(block1)
        rw_segment.write_data(block0)

        r_segment = rw_segment.to_read_only()

        self.assertEqual(r_segment.read_block(1), block1)


class TestReadWriteSegment(TestCase):
    def test_to_and_from_bytes(self):
        block_size = 64
        block = b'a' * block_size
        segment = ReadWriteSegment(123, block_size=block_size)
        block_number = segment.write_data(block)

        serialized = segment.to_bytes()
        deserialized = ReadOnlySegment(serialized, 123, block_size=block_size)

        self.assertEqual(deserialized.read_block(block_number)[:len(block)], block)

    def test_len_when_empty_should_be_zero(self):
        segment = ReadWriteSegment(123)

        self.assertEqual(len(segment), 0)

    def test_len_when_not_empty_should_equal_length_in_bytes(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        segment.write_data(block_bytes)

        self.assertEqual(len(segment), block_size)

    def test_to_read_only_should_return_a_read_only_segment_with_same_bytes(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        segment.write_data(block_bytes)
        segment.write_inode(block_bytes, 123)
        read_only = segment.to_read_only()

        self.assertIsInstance(read_only, ReadOnlySegment)
        self.assertEqual(read_only.to_bytes(), segment.to_bytes())

    def test_write_data_when_bytes_less_than_block_pads_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = (block_size // 2) * b'a'
        block_number = segment.write_data(block_bytes)

        padded_block = block_bytes + b'\0' * (block_size - len(block_bytes))

        self.assertEqual(segment.read_block(block_number), padded_block)
        self.assertEqual(block_number, 0)

    def test_write_inode_when_bytes_less_than_block_pads_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = (block_size // 2) * b'a'
        block_number = segment.write_inode(block_bytes, 123)

        padded_block = block_bytes + b'\0' * (block_size - len(block_bytes))

        self.assertEqual(segment.read_block(block_number), padded_block)
        self.assertEqual(block_number, 0)

    def test_write_data_when_bytes_is_a_full_block_does_not_pad_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        block_number = segment.write_data(block_bytes)

        self.assertEqual(segment.read_block(block_number), block_bytes)
        self.assertEqual(block_number, 0)

    def test_write_inode_when_bytes_is_a_full_block_does_not_pad_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        block_number = segment.write_inode(block_bytes, 123)

        self.assertEqual(segment.read_block(block_number), block_bytes)
        self.assertEqual(block_number, 0)

    def test_write_data_returns_the_block_number(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'

        for expected_block_number in range(5):
            returned_block_number = segment.write_data(block_bytes)
            self.assertEqual(returned_block_number, expected_block_number)

    def test_write_inode_returns_the_block_number(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'

        for expected_block_number in range(5):
            returned_block_number = segment.write_inode(block_bytes, 123)
            self.assertEqual(returned_block_number, expected_block_number)

    def test_is_full_when_fewer_than_max_block_count_written_returns_false(self):
        block_size = 64
        max_block_count = 16
        segment = ReadWriteSegment(123, block_size=block_size, max_block_count=max_block_count)
        block_bytes = block_size * b'a'

        for _ in range(max_block_count - 1):
            segment.write_data(block_bytes)

        self.assertFalse(segment.is_full())

    def test_is_full_when_max_block_count_blocks_written_returns_true(self):
        block_size = 64
        max_block_count = 16
        segment = ReadWriteSegment(123, block_size=block_size, max_block_count=max_block_count)
        block_bytes = block_size * b'a'

        for _ in range(max_block_count):
            segment.write_data(block_bytes)

        self.assertTrue(segment.is_full())

    def test_inode_block_numbers_should_return_a_list_of_inode_numbers_and_their_block_numbers(self):
        segment = ReadWriteSegment(123)
        inum0 = 111
        inum1 = 999
        segment.write_inode(b'abcd', inum0)
        segment.write_inode(b'abcd', inum1)

        self.assertEqual(segment.inode_block_numbers(), [(inum0, 0), (inum1, 1)])
