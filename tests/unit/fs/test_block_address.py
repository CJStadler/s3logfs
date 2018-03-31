import unittest

from s3logfs.fs import BlockAddress


class TestBlockAddress(unittest.TestCase):
    def test_to_and_from_bytes(self):
        address = BlockAddress(123, 456)
        packed_address = address.to_bytes()
        unpacked_address = BlockAddress(packed_address)

        self.assertEqual(unpacked_address.segmentid, address.segmentid)
        self.assertEqual(unpacked_address.offset, address.offset)

    def test_equality(self):
        self.assertEqual(BlockAddress(123, 456), BlockAddress(123, 456))
        self.assertNotEqual(BlockAddress(123, 456), BlockAddress(123, 999))
        self.assertNotEqual(BlockAddress(123, 456), BlockAddress(999, 456))

    def test_hash(self):
        self.assertEqual(hash(BlockAddress(123, 456)),
                         hash(BlockAddress(123, 456)))
        self.assertNotEqual(hash(BlockAddress(123, 456)),
                            hash(BlockAddress(123, 999)))
        self.assertNotEqual(hash(BlockAddress(123, 456)),
                            hash(BlockAddress(999, 456)))
