from boto3 import client


class S3Bucket:
    '''
    Provides methods for reading and writing to the S3 bucket specified by
    bucket_name. A single instance of this class should be instantiated on mount
    and used for all operations.
    '''
    CHECKPOINT_KEY = 'checkpoint'
    SEGMENT_PREFIX = 'seg_'
    SUPER_BLOCK_KEY = 'super_block'

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        self._client = client('s3')

    def get_checkpoint(self):
        return self._get_object(self.CHECKPOINT_KEY)

    def get_segment(self, segment_number):
        return self._get_object(self._segment_key(segment_number))

    def get_super_block(self):
        return self._get_object(self.SUPER_BLOCK_KEY)

    def put_checkpoint(self, checkpoint_bytes):
        self._put_object(self.CHECKPOINT_KEY, checkpoint_bytes)

    def put_segment(self, segment_number, segment_bytes):
        self._put_object(self._segment_key(segment_number), segment_bytes)

    def put_super_block(self, super_block_bytes):
        self._put_object(self.SUPER_BLOCK_KEY, super_block_bytes)

    # Private methods

    def _get_object(self, key):
        '''
        TODO: Handle errors
        '''
        response = self._client.get_object(
            Bucket=self._bucket_name,
            Key=key
        )
        return response['Body'].read()

    def _put_object(self, key, body):
        '''
        TODO: Handle errors
        '''
        response = self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=body
        )

    def _segment_key(self, segment_number):
        return self.SEGMENT_PREFIX + str(segment_number)
