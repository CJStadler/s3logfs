from pathlib import Path

from .backend_error import BackendError

class LocalDirectory:
    '''
    Stores data on disk.
    '''
    CHECKPOINT_KEY = 'checkpoint'
    SEGMENT_PREFIX = 'seg_'

    def __init__(self, bucket_name, parent_directory='/tmp/'):
        self._directory = Path(parent_directory) / bucket_name

    def create(self, acl='private', region=None):
        if not self._directory.exists():
            self._directory.mkdir()

    def get_checkpoint(self):
        return self._get_object(self.CHECKPOINT_KEY)

    def get_segment(self, segment_number):
        return self._get_object(self._segment_key(segment_number))

    def flush(self):
        pass

    def put_checkpoint(self, checkpoint_bytes):
        self._put_object(self.CHECKPOINT_KEY, checkpoint_bytes)

    def put_segment(self, segment_number, segment_bytes):
        self._put_object(self._segment_key(segment_number), segment_bytes)

    # Private methods

    def _get_object(self, key):
        path = self._directory / key

        try:
            with path.open('rb') as f:
                data = f.read()
        except FileNotFoundError as e:
            raise BackendError()

        return data

    def _put_object(self, key, body):
        path = self._directory / key

        with path.open('wb') as f:
            f.write(body)

    def _segment_key(self, segment_number):
        return self.SEGMENT_PREFIX + str(segment_number)
