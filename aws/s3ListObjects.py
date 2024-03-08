#!/usr/bin/env python3
import boto3


def s3List(env, s3Bucket):
    """Looks up an IP in the AWS tag list  based on the name passed.
    :Param env: aws environment
    :Param s3Bucket: name of the aws s3 bucket
    """
    # Grab the key for the proper environment.
    session = boto3.Session(profile_name=env, region_name="us-east-1")

    # Get all instances for this account.
    s3 = session.resource("s3")
    my_bucket = s3.Bucket(s3Bucket)

    for my_bucket_object in my_bucket.objects.all():
        print(my_bucket_object.key)


if __name__ == "__main__":
    env = ""
    s3Bucket = ""
    s3List(env, s3Bucket)
