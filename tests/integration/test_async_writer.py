from unittest import TestCase
from s3logfs.backends import S3Bucket, AsyncWriter

class TestAsyncWriter(TestCase):
    BUCKET_NAME = 's3logfs-integration-testing'

    def test_concurrent_writes(self):
        bucket = S3Bucket(self.BUCKET_NAME)
        max_segments_in_cache = 16
        max_workers = 8
        total_puts = 64

        with AsyncWriter(bucket, max_segments_in_cache, max_workers) as writer:
            for i in range(total_puts):
                writer.put_segment(i, self._segment_bytes(i))

                # These GET requests should be served from the cache if the
                # PUT has not completed.
                self.assertEqual(writer.get_segment(i), self._segment_bytes(i))

        # When the with block ends it should wait for all requests to complete,
        # so all segments should now be in S3.
        for i in range(total_puts):
            self.assertEqual(bucket.get_segment(i), self._segment_bytes(i))

    def _segment_bytes(self, i):
        return b'abcd' + bytes(str(i), encoding='utf-8')
