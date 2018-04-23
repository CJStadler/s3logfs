from .backend_error import BackendError

from contextlib import closing
from boto3 import client
from botocore.exceptions import ClientError

class S3Bucket:
    '''
    Provides methods for reading and writing to the S3 bucket specified by
    bucket_name. A single instance of this class should be instantiated on mount
    and used for all operations.
    '''
    CHECKPOINT_KEY = 'checkpoint'
    SEGMENT_PREFIX = 'seg_'

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        self._client = client('s3')

    def name(self):
        return self._bucket_name

    def create(self, acl='private', region=None):
        '''
        Creates the bucket. This succeeds even if the bucket already exists.
        '''
        request_args = {
            'ACL': acl,
            'Bucket': self._bucket_name,
        }

        if region:
            request_args['CreateBucketConfiguration'] = {
                'LocationConstraint': region}

        self._client.create_bucket(**request_args)

    def get_checkpoint(self):
        return self._get_object(self.CHECKPOINT_KEY)

    def get_segment(self, segment_number):
        return self._get_object(self._segment_key(segment_number))

    def flush(self):
        '''
        This class writes to S3 synchronously, so there is nothing to flush.
        '''
        pass

    def put_checkpoint(self, checkpoint_bytes):
        self._put_object(self.CHECKPOINT_KEY, checkpoint_bytes)

    def put_segment(self, segment_number, segment_bytes):
        self._put_object(self._segment_key(segment_number), segment_bytes)

    # Private methods

    def _get_object(self, key):
        '''
        TODO: Handle errors
        '''
        try:
            response = self._client.get_object(
                Bucket=self._bucket_name,
                Key=key
            )
        except ClientError as e:
            raise BackendError()

        with closing(response['Body']) as body:
            return body.read()

    def _put_object(self, key, body):
        '''
        TODO: Handle errors
        '''
        self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=body
        )

    def _segment_key(self, segment_number):
        return self.SEGMENT_PREFIX + str(segment_number)
