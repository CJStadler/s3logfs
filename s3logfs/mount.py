#!/usr/bin/env python3
import argparse

from sys import argv
from datetime import datetime
from .fuse_api import FuseApi
from .backends import S3Bucket, AsyncWriter, DiskCache, MemoryCache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mount',
                        help='The directory to mount the filesystem under.')
    parser.add_argument('bucket',
                        help='The name of the S3 bucket containing the filesystem.')
    parser.add_argument('-m', '--memcache', dest='memory_cache_size', type=int, default=16,
                        help='The maximum number of segments to hold in the in-memory cache (Default=16)')
    parser.add_argument('-d', '--diskcache', dest='disk_cache_size', type=int, default=64,
                        help='The maximum number of segments to hold in the on-disk cache (Default=64)')
    parser.add_argument('-w', '--writequeue', dest='write_queue_size', type=int, default=8,
                        help='The maximum number of segments waiting to be written '
                        'at a time. When the queue is full all new requests will wait. (Default=8)')
    parser.add_argument('-t', '--threads', dest='thread_pool_size', type=int, default=4,
                        help='The number of threads in the write request pool. (Default=4)')
    parser.add_argument('-c', '--checkpoint', dest='checkpoint_frequency', type=int, default=60,
                        help='The number of seconds between checkpoints. (Default=60)')
    args = parser.parse_args()

    bucket_name = args.bucket

    # for testing, if "TEST" is passed as the bucket name
    # a new bucket will be created with the current
    # datetime as the bucket name, otherwise it will be
    # named with what is passed as an argument
    if (bucket_name == "TEST"):
        bucket_name = datetime.now()
        print("DT: ", str(bucket_name))

    s3_bucket = S3Bucket(bucket_name)

    with AsyncWriter(s3_bucket, args.write_queue_size, args.thread_pool_size) as async_writer:
        with DiskCache(async_writer, args.disk_cache_size) as disk_cache:
            memory_cache = MemoryCache(disk_cache, args.memory_cache_size)
            FuseApi(args.mount, memory_cache, args.checkpoint_frequency)


if __name__ == '__main__':
    main()
