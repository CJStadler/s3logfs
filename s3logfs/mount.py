#!/usr/bin/env python3
import argparse

from sys import argv
from datetime import datetime
from .fuse_api import FuseApi
from .backends import S3Bucket, DiskCache, MemoryCache

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mount',
        help='The directory to mount the filesystem under.')
    parser.add_argument('bucket',
        help='The name of the S3 bucket containing the filesystem.')
    parser.add_argument('-m', '--memcache', dest='memory_cache_size', type=int, default=16,
                        help='The maximum number of segments to hold in the in-memory cache')
    parser.add_argument('-d', '--diskcache', dest='disk_cache_size', type=int, default=64,
                        help='The maximum number of segments to hold in the on-disk cache')
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

    with DiskCache(s3_bucket, args.disk_cache_size) as disk_cache:
        memory_cache = MemoryCache(disk_cache, args.memory_cache_size)
        FuseApi(args.mount, memory_cache)

if __name__ == '__main__':
    main()
