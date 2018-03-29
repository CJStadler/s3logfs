import unittest

from s3logfs.fs import BlockAddress

class TestBlockAddress(unittest.TestCase):
    def test_to_and_from_bytes(self):
        address = BlockAddress(123, 456)
        packed_address = address.to_bytes()
        unpacked_address = BlockAddress(packed_address)

        self.assertEqual(unpacked_address.segmentid, address.segmentid)
        self.assertEqual(unpacked_address.offset, address.offset)
