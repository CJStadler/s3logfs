# cs5600project
Team: Rene Adaimi, Brian Hayes, Christopher Stadler

Description:
  Implementation of a log-structured like file system on top of Amazon S3
  storage in user space via FUSE.

File System Requirements:
 - FUSE 3.5.X
   https://github.com/libfuse/libfuse/blob/master/README.md
 - Python 3.X
 - Boto3 (Amazon Python SDK)
   https://aws.amazon.com/sdk-for-python/

## Setup

Install s3logfs:
```
pip3 install -e path_to_repo
```

To create or mount a filesystem your AWS credentials must be configured
correctly for boto3 (See https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration).

To initialize an empty filesystem:
```
mkfs.s3logfs bucket_name
```
This will create a bucket with the given name (if it does not already exist) and
store configuration information in it. Run `mkfs.s3logfs --help` to see
additional options.

To mount:
```
mount.s3logfs directory_to_mount bucket_name
```

To unmount:
```
fusermount -u mount_directory
```

## Testing
Tests are divided into two groups: unit and integration. The main difference is
that unit tests mock out external requests (primarily to S3), while integration
tests do not. The purpose of unit tests is to fully test behavior in isolation,
while integration tests are for confirmation that units work together and with
external dependencies correctly

Integration tests require that your environment be configured to connect to S3,
and that you have access to a bucket named "s3logfs-integration-testing".
Integration tests are also much slower, and so should likely be run less
frequently during development.

The two suites can be run separately or together:
```sh
python3 -m unittest discover -s tests/unit/
python3 -m unittest discover -s tests/integration/
python3 -m unittest # Run all tests
python3 -m unittest tests.unit.fs.test_inode # Run specific module
```
