import unittest

from time import time
from s3logfs.fs import INode, BlockAddress


class TestINode(unittest.TestCase):
    def test_number_of_blocks(self):
        self.assertEqual(INode.NUMBER_OF_BLOCKS, 16)

    def test_struct_format(self):
        self.assertEqual(INode.STRUCT_FORMAT, 'ILI????LLL')

    def test_to_and_from_bytes(self):
        inode = INode()
        inode.inode_number = 123
        inode.size = 456
        inode.hard_links = 3
        inode.is_directory = True
        inode.readable = False
        inode.writable = True
        inode.executable = True
        t = int(time())
        inode.last_accessed_at = t - 1
        inode.last_modified_at = t - 2
        inode.status_last_changed_at = t - 3
        inode.block_addresses[INode.NUMBER_OF_BLOCKS - 1] = \
            BlockAddress(789, 99)
        out_bytes = inode.to_bytes()

        new_inode = INode.from_bytes(out_bytes)

        self.assertEqual(new_inode.inode_number, inode.inode_number)
        self.assertEqual(new_inode.size, inode.size)
        self.assertEqual(new_inode.hard_links, inode.hard_links)
        self.assertEqual(new_inode.is_directory, inode.is_directory)
        self.assertEqual(new_inode.readable, inode.readable)
        self.assertEqual(new_inode.writable, inode.writable)
        self.assertEqual(new_inode.executable, inode.executable)
        self.assertEqual(new_inode.last_accessed_at, inode.last_accessed_at)
        self.assertEqual(new_inode.last_modified_at, inode.last_modified_at)
        self.assertEqual(new_inode.status_last_changed_at,
                         inode.status_last_changed_at)
        self.assertEqual(new_inode.block_addresses, inode.block_addresses)
