from unittest import TestCase
from unittest.mock import Mock
from s3logfs.backends import S3Bucket

class TestS3Bucket(TestCase):
    def test_constants(self):
        self.assertEqual(S3Bucket.CHECKPOINT_KEY, 'checkpoint')
        self.assertEqual(S3Bucket.SEGMENT_PREFIX, 'seg_')

    def test_create(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        client = Mock()
        bucket._client = client

        bucket.create()

        client.create_bucket.assert_called_once_with(
            Bucket=bucket_name,
            ACL='private'
        )

    def test_create_with_region_and_acl(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        client = Mock()
        bucket._client = client
        acl = 'public-read'
        region = 'EU'
        
        bucket.create(acl=acl, region=region)

        client.create_bucket.assert_called_once_with(
            Bucket=bucket_name,
            ACL=acl,
            CreateBucketConfiguration={ 'LocationConstraint': region }
        )

    def test_get_checkpoint(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        body_bytes = b'abcd'
        client = self._client_get_mock(body_bytes)
        bucket._client = client

        result = bucket.get_checkpoint()

        self.assertEqual(result, body_bytes)
        client.get_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=S3Bucket.CHECKPOINT_KEY
        )

    def test_get_segment(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        body_bytes = b'abcd'
        client = self._client_get_mock(body_bytes)
        bucket._client = client

        result = bucket.get_segment(123)

        self.assertEqual(result, body_bytes)
        client.get_object.assert_called_once_with(
            Bucket=bucket_name,
            Key='seg_123'
        )

    def test_flush(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        bucket.flush()
        # No assertions because it is a no-op.

    def test_put_checkpoint(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        body_bytes = b'abcd'
        client = Mock()
        bucket._client = client

        result = bucket.put_checkpoint(body_bytes)

        client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=S3Bucket.CHECKPOINT_KEY,
            Body=body_bytes
        )

    def test_put_segment(self):
        bucket_name = 'test_bucket'
        bucket = S3Bucket(bucket_name)
        body_bytes = b'abcd'
        client = Mock()
        bucket._client = client

        result = bucket.put_segment(123, body_bytes)

        client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key='seg_123',
            Body=body_bytes
        )

    def _client_get_mock(self, body_bytes):
        body = Mock()
        body.read.return_value = body_bytes
        client = Mock()
        expected_response = {'Body': body}
        client.get_object.return_value = expected_response
        return client
