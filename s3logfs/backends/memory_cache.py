from cachetools import LRUCache
from .backend_wrapper import BackendWrapper

class MemoryCache(BackendWrapper):
    def __init__(self, backend, max_segments_in_cache):
        super().__init__(backend)
        self._segment_cache = LRUCache(maxsize=max_segments_in_cache)

    def get_segment(self, segment_number):
        if segment_number in self._segment_cache:
            segment_bytes = self._segment_cache[segment_number]
        else:
            segment_bytes = self._backend.get_segment(segment_number)
            self._segment_cache[segment_number] = segment_bytes

        return segment_bytes

    def put_segment(self, segment_number, segment_bytes):
        self._segment_cache[segment_number] = segment_bytes
        self._backend.put_segment(segment_number, segment_bytes)
