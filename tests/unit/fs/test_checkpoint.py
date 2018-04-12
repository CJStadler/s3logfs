from unittest import TestCase
from s3logfs.fs import CheckpointRegion, BlockAddress

class TestCheckpoint(TestCase):
    def test_to_and_from_bytes(self):
        segment_id = 999
        inode_id = 123
        inode_address = BlockAddress(456, 9)
        checkpoint = CheckpointRegion()
        checkpoint.inode_map[inode_id] = inode_address
        checkpoint._segment_counter = segment_id

        serialized = checkpoint.to_bytes()
        deserialized = CheckpointRegion.from_bytes(serialized)

        self.assertEqual(deserialized.current_segment_id(), segment_id)
        self.assertEqual(deserialized.inode_map[inode_id], inode_address)
