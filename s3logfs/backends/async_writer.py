from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Condition
from .backend_wrapper import BackendWrapper


class AsyncWriter(BackendWrapper):
    '''
    Handles writes asynchronously, using a thread pool. Also maintains an
    in-memory cache of segments that are in the process of being written.
    Otherwise a segment could be requested from the backend before it has been
    written. Once each write completes the segment is removed from this cache.
    '''
    def __init__(self, backend, max_segments_in_cache, max_workers):
        super().__init__(backend)
        self._max_segments_in_cache = max_segments_in_cache
        self._segments_being_written = {}  # segment_number -> data
        self._segments_being_written_cv = Condition()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._executor.shutdown()

    def get_segment(self, segment_number):
        segment_bytes = None
        with self._segments_being_written_cv:
            if segment_number in self._segments_being_written:
                segment_bytes = self._segments_being_written[segment_number]

        if not segment_bytes: # It was not in _segments_being_written
            segment_bytes = self._backend.get_segment(segment_number)

        return segment_bytes

    def put_segment(self, segment_number, segment_bytes):
        with self._segments_being_written_cv:
            self._segments_being_written_cv.wait_for(self._queue_not_full)
            self._segments_being_written[segment_number] = segment_bytes

        self._executor.submit(self._put_segment_async,
                              segment_number, segment_bytes)

    def put_checkpoint(self, checkpoint_bytes):
        self._executor.submit(self._put_checkpoint_async, checkpoint_bytes)

    def flush(self):
        with self._segments_being_written_cv:
            self._segments_being_written_cv.wait_for(self._queue_empty)

    def _put_segment_async(self, segment_number, segment_bytes):
        self._backend.put_segment(segment_number, segment_bytes)
        # TODO: Handle failure

        with self._segments_being_written_cv:
            del self._segments_being_written[segment_number]
            self._segments_being_written_cv.notify()

    def _put_checkpoint_async(self, checkpoint_bytes):
        self._backend.put_checkpoint(checkpoint_bytes)

    def _queue_not_full(self):
        return len(self._segments_being_written) < self._max_segments_in_cache

    def _queue_empty(self):
        return len(self._segments_being_written) == 0
