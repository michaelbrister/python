#!/usr/bin/env python3

# Query ec2 instance by IP and return it's tag Name value.
import boto3
import jmespath

def jmesPath(response):
# Using jmespath
    print("Result from jmespath")
    instance_name = jmespath.search("Reservations[].Instances[].Tags[?Key =='Name'].Value | [0]", response)
    print(instance_name[0])  

def loopQuery(response):
#  Looping over returned results
  print("Result from for loop")
  for r in result['Reservations']:
      for instance in r['Instances']:
          for tags in instance['Tags']:
              if tags['Key'] == 'Name':
                      server_name = tags['Value']
                      print(server_name)

if __name__ == "__main__":
  session = boto3.Session(profile_name="sandbox", region_name="us-east-1")
  ec2 = session.client('ec2')

  f = [{
      'Name': 'private-ip-address',
      'Values': ['x.x.x.x']
      }]
  result = ec2.describe_instances(Filters=f)
  
  jmesPath(result)
  loopQuery(result)
