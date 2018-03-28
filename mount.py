import argparse

from s3logfs import FuseApi

parser = argparse.ArgumentParser()
parser.add_argument('mount')
parser.add_argument('bucket')
args = parser.parse_args()

FuseApi(args.mount, args.bucket)
