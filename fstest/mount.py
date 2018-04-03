import argparse

from s3logfs import s3LogFS

parser = argparse.ArgumentParser()
parser.add_argument('mount')
parser.add_argument('bucket')
args = parser.parse_args()

s3LogFS(args.mount, args.bucket)
