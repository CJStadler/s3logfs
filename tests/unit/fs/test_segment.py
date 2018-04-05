from unittest import TestCase
from s3logfs.fs import ReadOnlySegment, ReadWriteSegment


class TestReadOnlySegment(TestCase):
    def test_bytes_should_return_segment_as_bytes(self):
        original_bytes = b'abcd'
        segment = ReadOnlySegment(original_bytes, 123)
        returned_bytes = segment.bytes()

        self.assertEqual(returned_bytes, original_bytes)
        self.assertTrue(isinstance(returned_bytes, bytes))

    def test_is_full_should_always_be_true(self):
        segment = ReadOnlySegment(b'abc', 123)

        self.assertTrue(segment.is_full())

    def test_read_block_should_return_the_block(self):
        block_size = 64
        block1 = b'x' * block_size
        block2 = b'a' * block_size
        segment = ReadOnlySegment(block1 + block2 + block1, 123,
            block_size=block_size)

        self.assertEqual(segment.read_block(1), block2)


class TestReadWriteSegment(TestCase):
    def test_bytes_when_empty_should_return_empty_bytes(self):
        segment = ReadWriteSegment(123)

        returned_bytes = segment.bytes()

        self.assertEqual(returned_bytes, b'')
        self.assertTrue(isinstance(returned_bytes, bytes))

    def test_bytes_when_not_empty_should_return_written_bytes(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        segment.write(block_bytes)

        returned_bytes = segment.bytes()

        self.assertEqual(returned_bytes, block_bytes)
        self.assertTrue(isinstance(returned_bytes, bytes))

    def test_len_when_empty_should_be_zero(self):
        segment = ReadWriteSegment(123)

        self.assertEqual(len(segment), 0)

    def test_len_when_not_empty_should_equal_length_in_bytes(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        segment.write(block_bytes)

        self.assertEqual(len(segment), block_size)

    def test_to_read_only_should_return_a_read_only_segment_with_same_bytes(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        segment.write(block_bytes)
        read_only = segment.to_read_only()

        self.assertIsInstance(read_only, ReadOnlySegment)
        self.assertEqual(read_only.bytes(), segment.bytes())

    def test_write_when_bytes_less_than_block_pads_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = (block_size // 2) * b'a'
        block_number = segment.write(block_bytes)

        padded_block = block_bytes + b'0' * (block_size - len(block_bytes))

        self.assertEqual(segment.read_block(block_number), padded_block)
        self.assertEqual(block_number, 0)

    def test_write_when_bytes_is_a_full_block_does_not_pad_the_block(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'
        block_number = segment.write(block_bytes)

        self.assertEqual(segment.read_block(block_number), block_bytes)
        self.assertEqual(block_number, 0)

    def test_write_returns_the_block_number(self):
        block_size = 64
        segment = ReadWriteSegment(123, block_size=block_size)
        block_bytes = block_size * b'a'

        for expected_block_number in range(5):
            returned_block_number = segment.write(block_bytes)
            self.assertEqual(returned_block_number, expected_block_number)

    def test_is_full_when_fewer_than_max_block_count_written_returns_false(self):
        block_size = 64
        max_block_count = 16
        segment = ReadWriteSegment(123, block_size=block_size, max_block_count=max_block_count)
        block_bytes = block_size * b'a'

        for _ in range(max_block_count - 1):
            segment.write(block_bytes)

        self.assertFalse(segment.is_full())

    def test_is_full_when_max_block_count_blocks_written_returns_true(self):
        block_size = 64
        max_block_count = 16
        segment = ReadWriteSegment(123, block_size=block_size, max_block_count=max_block_count)
        block_bytes = block_size * b'a'

        for _ in range(max_block_count):
            segment.write(block_bytes)

        self.assertTrue(segment.is_full())
