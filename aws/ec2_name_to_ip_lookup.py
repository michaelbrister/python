#!/usr/bin/env python3
import boto3

def rlookup(env, ec2_name):
    """Looks up an IP in the AWS tag list  based on the name passed."""
    # Grab the key for the proper environment.
    session = boto3.Session(profile_name=env, region_name="us-east-1")

    # Get all instances for this account.
    ec2 = session.resource('ec2')
    f = [{'Name': 'instance-state-name', 'Values': ['running']}]
    instances = ec2.instances.filter(Filters=f)
    # Find an instance that matches the name.
    output = []
    for i in instances:
        if i.tags:
            if i.tags is not None:
                for t in i.tags:
                    if t['Key'] == 'Name' and t['Value'] == ec2_name:
                        print(f"Found server at {i.private_ip_address}")
                        output.append(i.private_ip_address)
    return output

if __name__ == "__main__":

    env = ""
    ec2_name = ""
    machines = rlookup(env, ec2_name)
    print(len(machines))
    if len(machines) > 1:
        print("Please provide the name of an ec2 instance.")
