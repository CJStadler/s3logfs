#!/usr/bin/env python3
import argparse

from stat import S_IFDIR
from sys import argv
from time import time

from .fs import CheckpointRegion, Log, INode
from .backends import S3Bucket, LocalDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bucket_name',
                        help='The name of the S3 bucket containing the filesystem.')
    parser.add_argument('-b', '--blocksize', dest='block_size', type=int, default=4096,
                        help='The size of each block, in bytes. (Default=4096)')
    parser.add_argument('-s', '--segmentsize', dest='blocks_per_segment', type=int, default=512,
                        help='The number of blocks per segment. (Deafult=512)')
    parser.add_argument('-r', '--region', default=None,
                        help='The region to create the bucket in (see S3 documentation for options).')
    parser.add_argument('-l', '--local', dest='local_directory', default=None,
                        help='Create the filesystem under this local directory.')
    args = parser.parse_args()

    if args.local_directory:
        s3_bucket = LocalDirectory(args.bucket_name, parent_directory=args.local_directory)
    else:
        s3_bucket = S3Bucket(args.bucket_name)

    s3_bucket.create(region=args.region)

    checkpoint = CheckpointRegion(
        bucket=args.bucket_name,
        start_inode=0,
        block_size=args.block_size,
        blocks_per_segment=args.blocks_per_segment,
        checkpoint_time=time()
    )

    create_root_directory(checkpoint, s3_bucket)

    serialized_checkpoint = checkpoint.to_bytes()
    s3_bucket.put_checkpoint(serialized_checkpoint)


def create_root_directory(checkpoint, bucket):
    log = Log(
        checkpoint.next_segment_id(),
        bucket,
        checkpoint.block_size,
        checkpoint.segment_size
    )

    root_inode = INode()
    root_inode.inode_number = checkpoint.next_inode_id()
    root_inode.parent = root_inode.inode_number
    root_inode.block_size = checkpoint.block_size
    root_inode.mode = S_IFDIR | 0o777        # directory with 777 chmod
    root_inode.hard_links = 2     # "." and ".." make the first 2 hard links

    root_inode_addr = log.write_inode(
        root_inode.to_bytes(), root_inode.inode_number)
    log.flush()
    checkpoint.inode_map[root_inode.inode_number] = root_inode_addr
    checkpoint.root_inode_id = root_inode.inode_number


if __name__ == '__main__':
    main()
