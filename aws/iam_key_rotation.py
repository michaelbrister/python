#!/usr/bin/env python3

import argparse
import backoff
import boto3
import configparser
import logging
import time
from botocore.exceptions import ClientError
from pathlib import Path

logging.basicConfig(level=logging.INFO)

# https://stackoverflow.com/questions/54214786/boto3-iam-user-creation-failing-with-invalidclienttokenid-the-security-token-i
def backoff_hdlr(details):
    logging.info("Backing off {wait:0.1f} seconds afters {tries} tries "
           "calling function {target}".format(**details))

def getAccessKeys(session, userName):
    """ Returns number of access keys founce for IAM account.
        session -- boto3 session.
        username -- username in string format
    """
    iam = session.client('iam')

    paginator = iam.get_paginator('list_access_keys')
    for response in paginator.paginate(UserName=userName):
        return response

def verifyProfilesConfiguration(session, oldCredentials):
    """ Verifies aws profiles are found and can be read from 
        session -- boto3 session.
        oldCredentials -- dict 
        credentials = {
            'AccessKeyId': aws_access_key,
            'SecretAccessKey': aws_secret_key,
            'UserName': iam_username
        }
    """

    credentials = session.get_credentials()
    # logging.debug(credentials.access_key)
    # logging.debug(credentials.secret_key)

    if credentials.access_key is None:
        raise Exception(f"Could not find keys for profile.")
    else:
        oldCredentials['AccessKeyId'] = credentials.access_key
        oldCredentials['SecretAccessKey'] = credentials.secret_key

def createAccessKey(session, oldCredentials):
    """ Create new AWS IAM Access Key 

        session -- boto3 session.
        oldCredentials -- dict 
        credentials = {
            'AccessKeyId': aws_access_key,
            'SecretAccessKey': aws_secret_key,
            'UserName': iam_username
        }
    """
    # Create IAM client
    iam = session.client('iam')

    # Create a new access key
    try:
        response = iam.create_access_key(
            UserName=oldCredentials['UserName']
        )
        logging.info(response['AccessKey']['AccessKeyId'])
        return response
    except ClientError as e:
        logging.critical("There was an error creating the new IAM key.")
        logging.critical(e)

def getProfiles(aws_credentials_file):
    """ Returns list of configured profiles 
        profiles without a aws_access_key_id configured will be ommited. 
    """
    config = configparser.ConfigParser()
    config.read(aws_credentials_file)

    return [profile for profile in config.sections() if config[profile]['aws_access_key_id']]

def updateCredentialsFile(profile, newCredentials, aws_credentials_file):
    """ Update ./aws/credentials with new access key 
        profile -- string aws-profile name ( e.g. aws-sandbox )
        newCredentials -- type dict of newly created AWS keys
        aws_credentials_file -- string. Location of .aws/credentials file for user running the program.
        session -- boto3 session.

        Credentials -- dict 
        credentials = {
            'AccessKeyId': aws_access_key,
            'SecretAccessKey': aws_secret_key,
            'UserName': iam_username
        }
    """

    config = configparser.ConfigParser()
    config.read(aws_credentials_file)
    # set new access key / secret
    config.set(profile, "aws_access_key_id", newCredentials['AccessKey']['AccessKeyId'])
    config.set(profile, "aws_secret_access_key", newCredentials['AccessKey']['SecretAccessKey'])

    cfgfile = open(aws_credentials_file, 'w')
    config.write(cfgfile)
    cfgfile.close()

@backoff.on_exception(backoff.expo, 
                      ClientError,
                      on_backoff=backoff_hdlr, 
                      max_time=30)    
def deleteAccessKey(session, iamCredentials):
    """ Deletes old access key 
        session -- boto3 session.
        iamCredentials -- dict 
        iamCredentials = {
            'AccessKeyId': aws_access_key,
            'SecretAccessKey': aws_secret_key,
            'UserName': iam_username
        }
    """
    logging.info(f"Using session with access key {session.get_credentials().access_key}")

    # Create IAM client
    iam = session.client('iam')

    # Delete access key
    iam.delete_access_key(
        AccessKeyId=iamCredentials['AccessKeyId'],
        UserName=iamCredentials['UserName']
    )

def main():
    """ Main function of the program """
    # Grab command line arguments
    parser = argparse.ArgumentParser(description='Rotates AWS IAM Keys for specified profile(s)')
    parser.add_argument('-p', '--profiles', type=str, help='List of comma seperated AWS Profiles to update')
    parser.add_argument('-f', '--force', default=False, action="store_true", help="When there are two access keys, deletes the access key the current request is not using. ")
    parser.add_argument('--safe', default=False, action='store_true', help='Backs up the current config. And only deactivates the old key.')
    parser.add_argument('--apply', default=False, action='store_true', help='Performs the key rotation instead of just doing a check.')

    # TODO    
    # make dry-run default
    # Safe mode to just create new and de-activate old.
    
    args = parser.parse_args()

    # set path to aws_credentials_file
    aws_credentials_file = Path(f"{str(Path.home())}/.aws/credentials")

    # Check if credentials file exists
    if not Path.exists(aws_credentials_file):
        logging.critical("Unable to locate aws credentials file. Exiting")
        raise Exception("Unable to locate aws credentials file. Exiting")

    # If profiles is passed in use those instead of default list
    if args.profiles is None:
        # lookup configured credentials for list of profiles.
        PROFILES = getProfiles(aws_credentials_file)
    else:
        PROFILES = args.profiles.split(',')

    logging.info(f"Rotating keys for profile(s) { ' '.join(PROFILES) }")

    for profile in PROFILES:
        logging.info(f"Rotating keys for {profile}")
        oldCredentials = {}
        newCredentials = {}

        session = boto3.Session(profile_name=profile, region_name="us-east-1")

        # Gets username associated with current IAM profile
        iam = session.resource('iam')
        oldCredentials['UserName'] = iam.CurrentUser().user_name
        
        # checks number of access keys configured for user.
        # if more than 1 key is found key loop is skipped.
        iamKeys = getAccessKeys(session, oldCredentials['UserName'])

        if len(iamKeys['AccessKeyMetadata']) > 1 and args.force == False:
            logging.info (f"Multiple access keys found and force flag is not set, unable to rotate keys for profile {profile}.")
            exit()

        if len(iamKeys['AccessKeyMetadata']) > 1 and args.force:
            logging.info("Multiple Access keys found, force flag is set. Deleting unused access key.")

            # current access key
            logging.info(f"session access key {session.get_credentials().access_key}")

            # get unused access keys & deletes it.
            logging.info(next((key['AccessKeyId'] for key in iamKeys['AccessKeyMetadata'] if key['AccessKeyId'] != session.get_credentials().access_key), None))
            # uses next function to iterate over list comprehension to get the key that is not the key used in the current boto3 session.
            oldCredentials['AccessKeyId'] = next((key['AccessKeyId'] for key in iamKeys['AccessKeyMetadata'] if key['AccessKeyId'] != session.get_credentials().access_key), None)

            logging.info("AWS IAM APIs employ an eventually consistent model\nSleeping to allow AWS time to propigate the keys.")
            time.sleep(5)

            # delete unused key
            deleteAccessKey(session, oldCredentials)

        logging.info(f"Gathering {profile} credentials")
        verifyProfilesConfiguration(session, oldCredentials)

        logging.info("Creating new access key")
        newCredentials = createAccessKey(session, oldCredentials)

        # Creates session using the new access key we just created
        new_session = boto3.Session( aws_access_key_id=newCredentials['AccessKey']['AccessKeyId'], 
                                     aws_secret_access_key=newCredentials['AccessKey']['SecretAccessKey'],
                                     region_name="us-east-1"
        )

        # Update the ./aws/credentials file with the new access key
        updateCredentialsFile(profile, newCredentials, aws_credentials_file)

        # Delete old access key from AWS
        logging.info("Deleting old IAM credentials")

        deleteAccessKey(new_session, oldCredentials)
    
if __name__ == "__main__":
    main()
