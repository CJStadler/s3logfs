from unittest import TestCase
from s3logfs import S3Bucket
from s3logfs.fs import Log, ReadOnlySegment, ReadWriteSegment


class TestLog(TestCase):
    BUCKET_NAME = 's3logfs-integration-testing'

    def test_write_and_read(self):
        segment_size = ReadOnlySegment.BLOCK_SIZE * 3
        block_number = 1
        block = ReadOnlySegment.BLOCK_SIZE * b'a'

        last_segment_number = 123
        bucket = S3Bucket(self.BUCKET_NAME)
        log = Log(segment_size, last_segment_number, bucket)

        log.write(ReadOnlySegment.BLOCK_SIZE * b'x')
        address = log.write(block)
        log.write(ReadOnlySegment.BLOCK_SIZE * b'x')

        result = log.read(*address)
        self.assertEqual(result, block)
