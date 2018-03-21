import boto3
import time
import sys
import random

s3 = boto3.client('s3')

# create block of 4096 random bytes
data = bytearray()
for b in range(1,4096):
  data.append(random.randint(1,250))

time1 = time.time()

# write block to s3 bucket
response = s3.put_object(
       ACL='private',
       Body=data,
       Bucket='s3logfs-03-20-2018',
       Key='0');

time2 = time.time()

print( str((time2-time1)*1000) + 'ms' )

# test write to disk
smFile = open('./small.txt','w')

time1 = time.time()
smFile.write(data);
time2 = time.time()
print( str((time2-time1)*1000) + 'ms' )

# create block of 4MB random bytes
data = bytearray()
for b in range(1,4096*512):
  data.append(random.randint(1,250))

time1 = time.time()

# write block to s3 bucket
response = s3.put_object(
       ACL='private',
       Body=data,
       Bucket='s3logfs-03-20-2018',
       Key='0');

time2 = time.time()

print( str((time2-time1)*1000) + 'ms' )

# test write to disk
lgFile = open('./small.txt','w')

time1 = time.time()
lgFile.write(data);
time2 = time.time()
print( str((time2-time1)*1000) + 'ms' )
