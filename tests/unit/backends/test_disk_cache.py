from unittest import TestCase
from pathlib import Path
from s3logfs.backends import DiskCache
from unittest.mock import Mock, call


class TestDiskCache(TestCase):
    def test_constants(self):
        self.assertEqual(DiskCache.DIRECTORY_NAME, 's3logfs_cache')

    def test_parent_directory_is_tmp_by_default(self):
        segment_bytes = b'abc'
        backend = Mock()
        backend.get_segment.return_value = segment_bytes

        with DiskCache(backend, 123) as cache:
            segment_number = 123
            cache.get_segment(segment_number)
            file = Path('/tmp') / DiskCache.DIRECTORY_NAME / str(segment_number)
            self.assertTrue(file.exists())

    def test_specified_parent_directory_used(self):
        segment_bytes = b'abc'
        backend = Mock()
        backend.get_segment.return_value = segment_bytes
        parent_directory = Path('/tmp/test_cache_parent/')
        parent_directory.mkdir()

        try:
            with DiskCache(backend, 123, parent_directory=str(parent_directory)) as cache:
                segment_number = 123
                cache.get_segment(segment_number)
                file = parent_directory / DiskCache.DIRECTORY_NAME / \
                    str(segment_number)
                self.assertTrue(file.exists())
        finally:
            parent_directory.rmdir()

    def test_exit_removes_the_cache(self):
        segment_bytes = b'abc'
        backend = Mock()
        backend.get_segment.return_value = segment_bytes

        with DiskCache(backend, 123) as cache:
            cache.get_segment(123)

        directory = Path('/tmp') / DiskCache.DIRECTORY_NAME
        self.assertFalse(directory.exists())

    def test_get_segment_should_limit_cache_size(self):
        backend = Mock()
        backend.get_segment.return_value = b'abc'
        max_segments_in_cache = 3

        with DiskCache(backend, max_segments_in_cache) as cache:
            for i in range(max_segments_in_cache + 1):
                cache.get_segment(i)  # Should miss
                cache.get_segment(i)  # Should hit

            cache.get_segment(1)  # Should hit
            cache.get_segment(0)  # Should miss because 0 was evicted

            calls = [call(x)
                     for x in list(range(max_segments_in_cache + 1)) + [0]]
            backend.get_segment.assert_has_calls(calls)

    def test_get_segment_should_return_the_value_from_the_backend(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()
        backend.get_segment.return_value = segment_bytes

        with DiskCache(backend, 123) as cache:
            uncached_response = cache.get_segment(segment_number)
            cached_response = cache.get_segment(segment_number)

            backend.get_segment.assert_called_once_with(segment_number)
            self.assertEqual(uncached_response, segment_bytes)
            self.assertEqual(cached_response, segment_bytes)

    def test_put_segment_should_be_forwarded_to_the_backend(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()

        with DiskCache(backend, 123) as cache:
            cache.put_segment(segment_number, segment_bytes)

            backend.put_segment.assert_called_once_with(
                segment_number, segment_bytes)

    def test_put_segment_should_write_to_cache(self):
        segment_bytes = b'abc'
        segment_number = 123
        backend = Mock()

        with DiskCache(backend, 123) as cache:
            cache.put_segment(segment_number, segment_bytes)
            result = cache.get_segment(segment_number)

            backend.get_segment.assert_not_called()
            self.assertEqual(result, segment_bytes)

    def test_get_checkpoint_should_be_forwarded_to_the_backend(self):
        checkpoint_bytes = b'abc'
        backend = Mock()
        backend.get_checkpoint.return_value = checkpoint_bytes

        with DiskCache(backend, 123) as cache:
            result = cache.get_checkpoint()

            self.assertEqual(result, checkpoint_bytes)
            backend.get_checkpoint.assert_called_once_with()

    def test_put_checkpoint_should_be_forwarded_to_the_backend(self):
        checkpoint_bytes = b'abc'
        backend = Mock()

        with DiskCache(backend, 123) as cache:
            cache.put_checkpoint(checkpoint_bytes)

            backend.put_checkpoint.assert_called_once_with(checkpoint_bytes)
