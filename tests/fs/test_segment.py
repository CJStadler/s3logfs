from unittest import TestCase
from s3logfs.fs import ReadOnlySegment, ReadWriteSegment


class TestReadOnlySegment(TestCase):
    def test_bytes(self):
        bytes = b'abcd'
        seg = ReadOnlySegment(bytes)
        self.assertEqual(seg.bytes(), bytes)

    def test_read_when_block_number_valid(self):
        block1 = b'x' * ReadOnlySegment.BLOCK_SIZE
        block2 = b'a' * ReadOnlySegment.BLOCK_SIZE
        seg = ReadOnlySegment(block1 + block2 + block1)
        self.assertEqual(seg.read(1), block2)


class TestReadWriteSegment(TestCase):
    def test_bytes_when_empty(self):
        seg = ReadWriteSegment()
        self.assertEqual(seg.bytes(), b'')

    def test_bytes_when_not_empty(self):
        bytes = ReadWriteSegment.BLOCK_SIZE * b'a'
        seg = ReadWriteSegment()
        seg.write(bytes)
        self.assertEqual(seg.bytes(), bytes)

    def test_len_when_empty(self):
        seg = ReadWriteSegment()
        self.assertEqual(len(seg), 0)

    def test_len_when_not_empty(self):
        bytes = ReadWriteSegment.BLOCK_SIZE * b'a'
        seg = ReadWriteSegment()
        seg.write(bytes)
        self.assertEqual(len(seg), ReadWriteSegment.BLOCK_SIZE)

    def test_to_read_only(self):
        bytes = ReadWriteSegment.BLOCK_SIZE * b'a'
        seg = ReadWriteSegment()
        seg.write(bytes)
        read_only = seg.to_read_only()
        self.assertIsInstance(read_only, ReadOnlySegment)
        self.assertEqual(read_only.bytes(), bytes)

    def test_write_when_bytes_larger_than_block(self):
        bytes = (ReadWriteSegment.BLOCK_SIZE + 1) * b'a'
        seg = ReadWriteSegment()
        self.assertRaises(RuntimeError, seg.write, bytes)

    def test_write_when_bytes_less_than_block(self):
        bytes = (ReadWriteSegment.BLOCK_SIZE - 1) * b'a'
        seg = ReadWriteSegment()
        seg.write(bytes)
        block_number = seg.write(bytes)
        padded_block = bytes + bytearray([0])
        self.assertEqual(seg.bytes(), 2 * padded_block)
        self.assertEqual(block_number, 1)

    def test_write_when_bytes_is_a_full_block(self):
        bytes = (ReadWriteSegment.BLOCK_SIZE) * b'a'
        seg = ReadWriteSegment()
        seg.write(bytes)
        block_number = seg.write(bytes)
        self.assertEqual(seg.bytes(), 2 * bytes)
        self.assertEqual(block_number, 1)
