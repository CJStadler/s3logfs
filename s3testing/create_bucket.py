import boto3
import time

s3 = boto3.client('s3')
time1 = time.time()
response = s3.create_bucket(Bucket='s3logfs-03-20-2018')
time2 = time.time()
print(response)
print('Create Time:', str((time2-time1)*1000.0)+'ms')

#time3 = time.time()
#response = s3.delete_bucket(Bucket='s3logfs-03-20-2018')
#time4 = time.time()
#print(response)
#print('Delete Time:', str((time4-time3)*1000.0)+'ms')
