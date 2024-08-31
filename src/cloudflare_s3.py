import os
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError


def get_bucket(secrets):
    s3 = boto3.resource(
    's3',
    endpoint_url=secrets['bucket']['endpoint_url'],
    aws_access_key_id=secrets['bucket']['aws_access_key_id'],
    aws_secret_access_key=secrets['bucket']['aws_secret_access_key'],
    config=Config(proxies=None),
    )
    bucket = s3.Bucket(secrets['bucket']['bucket_name'])
    return bucket

def upload_file(local_path, obj_name, bucket):
    success = True
    try:
        bucket.upload_file(local_path, obj_name)
    except BotoCoreError as err:
        print(err)
        success = False
    return success

def upload_files(dir, bucket, file_extensions=['rss','m4a']):
    success_count = 0
    for root, dirs, files in os.walk(dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in file_extensions):
                local_path = os.path.join(root, file)
                obj_name = file
                if upload_file(local_path, obj_name, bucket):
                    success_count += 1
    return success_count

def delete_files(invalid_episodes, bucket):
    if invalid_episodes:
        obj_list = [{'Key':f'{x[0]}.m4a'} for x in invalid_episodes]
        bucket.delete_objects(Delete={"Objects": obj_list})