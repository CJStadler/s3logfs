from unittest import TestCase
from s3logfs import S3Bucket
from s3logfs.fs import Log, ReadOnlySegment, ReadWriteSegment


class TestLog(TestCase):
    BUCKET_NAME = 's3logfs-integration-testing'

    def test_write_and_read(self):
        segment_id = 123
        bucket = S3Bucket(self.BUCKET_NAME)
        log = Log(segment_id, bucket)

        segment_size = log.get_block_size() * 3
        block_number = 1
        block = log.get_block_size() * b'a'

        log.write(log.get_block_size() * b'x')
        address = log.write(block)
        log.write(log.get_block_size() * b'x')

        result = log.read(address)
        self.assertEqual(result, block)
