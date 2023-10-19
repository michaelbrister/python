#!/usr/bin/env python3 

import base64
import boto3
import rsa

instance_id = ''
profile = ''
region = ''
env = ''
key_path = ''

def decrypt_ec2_pass(instance):
    """ Get AWS credentials
    :Param instance: ec2 instance
    """
    session = boto3.Session(profile_name=profile)
    credentials = session.get_credentials()

    ec2 = session.client('ec2', region_name=region)
    instance = ec2.get_password_data(InstanceId=instance)

    ecrypted_pass = base64.b64decode(instance['PasswordData'])

    if (ecrypted_pass):
        with open (key_path,'r') as privkeyfile:
            priv = rsa.PrivateKey.load_pkcs1(privkeyfile.read())
        key = rsa.decrypt(ecrypted_pass,priv)
    else:
        key = 'Wait at least 4 minutes after creation before the admin password is available'
    return key.decode('utf-8')
 

if __name__ == "__main__":
    password = decrypt_ec2_pass(instance_id)
    print(password)
