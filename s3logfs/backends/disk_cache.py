from collections import OrderedDict
from pathlib import Path
from shutil import rmtree
from .backend_wrapper import BackendWrapper

class DiskCache(BackendWrapper):
    '''
    Implements a LRU cache, with data stored on disk.

    Also implements the context manager API so that it can be instantiated in a
    with block to ensure cleanup.
    '''

    DIRECTORY_NAME = 's3logfs_cache'

    def __init__(self, backend, max_segments_in_cache, parent_directory='/tmp'):
        super().__init__(backend)
        self._max_segments_in_cache = max_segments_in_cache
        self._cache_directory = Path(parent_directory) / self.DIRECTORY_NAME
        self._cache_directory.mkdir()
        self._cached_segment_numbers = OrderedDict() # Keys are segment numbers, values don't matter.

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        rmtree(str(self._cache_directory))

    def get_segment(self, segment_number):
        if segment_number in self._cached_segment_numbers:
            segment_bytes = self._cache_read(segment_number)
        else:
            segment_bytes = self._backend.get_segment(segment_number)
            self._cache_insert(segment_number, segment_bytes)

        return segment_bytes

    def put_segment(self, segment_number, segment_bytes):
        self._cache_insert(segment_number, segment_bytes)
        self._backend.put_segment(segment_number, segment_bytes)

    # Private methods

    def _cache_read(self, segment_number):
        path = self._path_for_segment(segment_number)

        with path.open('rb') as f:
            segment_bytes = f.read()

        self._cached_segment_numbers.move_to_end(segment_number)

        return segment_bytes

    def _cache_insert(self, segment_number, segment_bytes):
        path = self._path_for_segment(segment_number)

        # TODO: Make this async?
        with path.open('wb') as f:
            f.write(segment_bytes)

        self._cached_segment_numbers[segment_number] = None

        if len(self._cached_segment_numbers) > self._max_segments_in_cache:
            self._cached_segment_numbers.popitem(last=False)


    def _path_for_segment(self, segment_number):
        return self._cache_directory / str(segment_number)
