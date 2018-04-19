import unittest

import math

from time import time
from s3logfs.fs import INode, BlockAddress
from stat import S_IFDIR


class TestINode(unittest.TestCase):
    def test_number_of_direct_blocks(self):
        self.assertEqual(INode.NUMBER_OF_DIRECT_BLOCKS, 16)

    def test_struct_format(self):
        self.assertEqual(INode.STRUCT_FORMAT, 'QQQIIIIIIIddd')

    def test_to_and_from_bytes(self):
        inode = INode()
        inode.inode_number = 123
        inode.parent = 1
        inode.size = 456
        inode.block_size = 4096
        inode.mode = S_IFDIR | 0o077
        inode.hard_links = 3
        t = time()
        inode.last_accessed_at = t
        inode.last_modified_at = t
        inode.status_last_changed_at = t
        inode.block_addresses[INode.NUMBER_OF_DIRECT_BLOCKS-1] = \
            BlockAddress(789, 99)
        out_bytes = inode.to_bytes()

        new_inode = INode.from_bytes(out_bytes)

        self.assertEqual(new_inode.inode_number, inode.inode_number)
        self.assertEqual(new_inode.size, inode.size)
        self.assertEqual(new_inode.block_size, inode.block_size)
        self.assertEqual(new_inode.mode, inode.mode)
        self.assertEqual(new_inode.hard_links, inode.hard_links)
        self.assertEqual(new_inode.last_accessed_at, inode.last_accessed_at)
        self.assertEqual(new_inode.last_modified_at, inode.last_modified_at)
        self.assertEqual(new_inode.status_last_changed_at, inode.status_last_changed_at)
        self.assertEqual(new_inode.block_addresses, inode.block_addresses)

    def test_from_padded_bytes(self):
        inode = INode()
        inode.inode_number = 123
        inode.parent = 1
        inode.block_size = 4096
        inode.size = 2 * inode.block_size
        inode.mode = S_IFDIR | 0o077
        inode.hard_links = 3
        t = time()
        inode.last_accessed_at = t
        inode.last_modified_at = t
        inode.status_last_changed_at = t

        inode.block_addresses[0] = BlockAddress(123, 12)
        inode.block_addresses[1] = BlockAddress(456, 45)

        out_bytes = inode.to_bytes()
        padding = (inode.block_size - len(out_bytes)) * b'\0'

        new_inode = INode.from_bytes(out_bytes + padding)

        self.assertEqual(new_inode.block_addresses, inode.block_addresses)
