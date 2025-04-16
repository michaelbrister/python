#!/usr/bin/env python3

# Query ec2 instance by IP and return it's tag Name value.
import boto3
import jmespath
import time


def jmesPath(response) -> string:
    """
    Searches response using jmespath to query name tag
    :Param response:
    :return instance_name:
    """
    print("Result from jmespath")
    instance_name = jmespath.search(
        "Reservations[].Instances[].Tags[?Key =='Name'].Value | [0][0]", response
    )
    print(instance_name)


def loopQuery(response) -> instance_name:
    """
    Looping over response searching for name tag
    :Param response:
    :return instance_name:
    """
    print("Result from for loop")
    for r in response["Reservations"]:
        for instance in r["Instances"]:
            for tags in instance["Tags"]:
                if tags["Key"] == "Name":
                    server_name = tags["Value"]
                    print(server_name)


if __name__ == "__main__":
    session = boto3.Session(profile_name="sandbox", region_name="us-east-1")
    ec2 = session.client("ec2")

    f = [{"Name": "private-ip-address", "Values": ["x.x.x.x"]}]
    result = ec2.describe_instances(Filters=f)

    start_time = time.perf_counter()
    instance_name = jmesPath(result)
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"jmesPath function took {execution_time:.4f}")

    start_time = time.perf_counter()
    instance_name = loopQuery(result)
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"loop function took {execution_time.4f}")