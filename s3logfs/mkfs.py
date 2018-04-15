#!/usr/bin/env python3
import argparse

from sys import argv
from datetime import datetime
from .fs import CheckpointRegion
from .backends import S3Bucket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bucket_name',
                        help='The name of the S3 bucket containing the filesystem.')
    parser.add_argument('-b', '--blocksize', dest='block_size', type=int, default=4096,
                        help='The size of each block, in bytes.')
    parser.add_argument('-s', '--segmentsize', dest='blocks_per_segment', type=int, default=512,
                        help='The number of blocks per segment.')
    parser.add_argument('-r', '--region', default=None,
                        help='The region to create the bucket in (see S3 documentation for options).')
    args = parser.parse_args()

    s3_bucket = S3Bucket(args.bucket_name)
    s3_bucket.create(region=args.region)

    checkpoint = CheckpointRegion(
        block_size=args.block_size, blocks_per_segment=args.blocks_per_segment)
    serialized_checkpoint = checkpoint.to_bytes()

    s3_bucket.put_checkpoint(serialized_checkpoint)


if __name__ == '__main__':
    main()
