from unittest import TestCase
from s3logfs.backends import S3Bucket, AsyncWriter, DiskCache, MemoryCache
from s3logfs.fs import BlockAddress, Log


class TestLog(TestCase):
    BUCKET_NAME = 's3logfs-integration-testing'

    def test_write_and_read_to_s3(self):
        current_segment_id = 123
        block_size = 64
        blocks_per_segment = 8
        address = BlockAddress(current_segment_id, blocks_per_segment // 2)
        bucket = S3Bucket(self.BUCKET_NAME)
        expected_block_bytes = block_size * b'a'

        # First, write enough blocks to put a segment to S3
        with AsyncWriter(bucket, 8, 4) as async_writer:
            with DiskCache(async_writer, 32) as disk_cache:
                memory_cache = MemoryCache(disk_cache, 8)
                log = Log(current_segment_id, memory_cache,
                          block_size=block_size, blocks_per_segment=blocks_per_segment)

                for i in range(blocks_per_segment):
                    if i == address.offset:
                        block_bytes = expected_block_bytes
                    else:
                        block_bytes = block_size * b'x'
                    log.write_data_block(block_bytes)

                result = log.read_block(address) # Should be read from cache
                self.assertEqual(result, expected_block_bytes)

        # Attempt read from a fresh cache
        with AsyncWriter(bucket, 8, 4) as async_writer:
            with DiskCache(async_writer, 32) as disk_cache:
                memory_cache = MemoryCache(disk_cache, 8)
                log = Log(current_segment_id + 1, memory_cache,
                          block_size=block_size, blocks_per_segment=blocks_per_segment)

                result = log.read_block(address)
                self.assertEqual(result, expected_block_bytes)

    def test_written_blocks_should_be_in_s3_after_flush(self):
        current_segment_id = 123
        block_size = 64
        blocks_per_segment = 8
        address = BlockAddress(current_segment_id, 0)
        bucket = S3Bucket(self.BUCKET_NAME)
        expected_block_bytes = block_size * b'a'

        # Write a single block and flush
        with AsyncWriter(bucket, 8, 4) as async_writer:
            with DiskCache(async_writer, 32) as disk_cache:
                memory_cache = MemoryCache(disk_cache, 8)
                log = Log(current_segment_id, memory_cache,
                          block_size=block_size, blocks_per_segment=blocks_per_segment)

                log.write_data_block(expected_block_bytes)
                log.flush()

        # Attempt read from a fresh cache
        with AsyncWriter(bucket, 8, 4) as async_writer:
            with DiskCache(async_writer, 32) as disk_cache:
                memory_cache = MemoryCache(disk_cache, 8)
                log = Log(current_segment_id + 1, memory_cache,
                          block_size=block_size, blocks_per_segment=blocks_per_segment)

                result = log.read_block(address)
                self.assertEqual(result, expected_block_bytes)
