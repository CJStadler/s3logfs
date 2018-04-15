from unittest import TestCase
from time import sleep
from s3logfs.backends import AsyncWriter
from unittest.mock import Mock, call

class TestAsyncWriter(TestCase):
    def test_put_segment_should_limit_number_of_threads(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()
        backend.put_segment.side_effect = lambda _a, _b: sleep(0.01)
        max_workers = 3

        with AsyncWriter(backend, max_workers + 1, max_workers) as cache:
            for i in range(max_workers + 1):
                cache.put_segment(i, segment_bytes)
            self.assertEqual(backend.put_segment.call_count, max_workers)

    def test_put_segment_should_be_forwarded_to_the_backend(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()

        with AsyncWriter(backend, 4, 2) as cache:
            cache.put_segment(segment_number, segment_bytes)

        backend.put_segment.assert_called_once_with(
            segment_number, segment_bytes)

    def test_put_segment_should_cache_segment_while_writing(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()
        backend.put_segment.side_effect = lambda _a, _b: sleep(0.01)

        with AsyncWriter(backend, 4, 2) as cache:
            cache.put_segment(segment_number, segment_bytes)
            cache.get_segment(segment_number) # Cache hit
            backend.get_segment.assert_not_called()

        cache.get_segment(segment_number) # Cache miss
        backend.get_segment.assert_called_once_with(segment_number)

    def test_put_segment_should_wait_if_cache_is_full(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()
        backend.put_segment.side_effect = lambda _a, _b: sleep(0.01)
        cache_size = 3

        with AsyncWriter(backend, cache_size, 2) as cache:
            for i in range(cache_size):
                cache.put_segment(i, segment_bytes)
            cache.put_segment(segment_number, segment_bytes)
            self.assertLessEqual(len(cache._segments_being_written), cache_size)

    def test_get_checkpoint_should_be_forwarded_to_the_backend(self):
        checkpoint_bytes = b'abc'
        backend = Mock()
        backend.get_checkpoint.return_value = checkpoint_bytes

        with AsyncWriter(backend, 4, 2) as cache:
            result = cache.get_checkpoint()

            self.assertEqual(result, checkpoint_bytes)
            backend.get_checkpoint.assert_called_once_with()

    def test_put_checkpoint_should_be_performed_async(self):
        checkpoint_bytes = b'abc'
        backend = Mock()

        with AsyncWriter(backend, 4, 2) as cache:
            cache.put_checkpoint(checkpoint_bytes)

        backend.put_checkpoint.assert_called_once_with(checkpoint_bytes)

    def test_flush_should_wait_for_writes_to_complete(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()
        backend.put_segment.side_effect = lambda _a, _b: sleep(0.01)
        cache_size = 3

        with AsyncWriter(backend, cache_size, 2) as cache:
            for i in range(cache_size):
                cache.put_segment(i, segment_bytes)
            cache.flush()
            self.assertEqual(len(cache._segments_being_written), 0)
