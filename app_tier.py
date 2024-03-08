"""
    This code should be placed on the EC2 instances running the deep learning model.
    Note: 
        1. Code assumes that the deep learning model script is located at /home/ubuntu/classifier/image_classification.py 
        2. The output file output.txt is generated by that script. 
        3. Modify the paths depending on your setup. 
        4. Also, replace 'your-response-bucket-name' with the name of the S3 bucket where the recognition results will be stored.
"""

import sys
import boto3
import subprocess
import os
import json
import yaml
import pathlib
import socket
import time

# Set up credentialss
settings_path = pathlib.Path(__file__).parent.parent.parent.absolute() / "home/ubuntu/settings.yaml"
with open(settings_path, "r") as infile:
        CONFIG = yaml.safe_load(infile)

# put some credentials in the environment
os.environ["AWS_ACCESS_KEY_ID"] = CONFIG["aws_settings"]["AWSAccessKeyID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = CONFIG["aws_settings"]["AWSSecretAccessKey"]
os.environ["AWS_DEFAULT_REGION"] = CONFIG["aws_settings"]["AWSDefaultRegion"]

sqs = boto3.resource('sqs', region_name='us-east-1')
s3 = boto3.resource('s3', region_name='us-east-1')
s3_client = boto3.client('s3')
request_queue = sqs.get_queue_by_name(QueueName='requestQueue')
response_queue = sqs.get_queue_by_name(QueueName='responseQueue')
response_queue_url = response_queue.url
input_bucket_name = 'inputbucket546'
output_bucket_name = 'outputbucket546'

#get instance id
session = boto3.Session(region_name="us-east-1")
ec2_client = session.client('ec2')
instance_id = ec2_client.describe_instances()['Reservations'][0]['Instances'][0]['InstanceId']
print(instance_id)
init_sleep = True

while True:
    # Receive messages from the request queue
    messages = request_queue.receive_messages(MaxNumberOfMessages=3, WaitTimeSeconds=0)
    if messages:
        if init_sleep:
            time.sleep(90)
            init_sleep = False
        # Process each message
        for message in messages:
            print(message.body)
            message_dict = eval(message.body) # Convert string to dictionary
            image_name = message_dict['image_filename']
            print(image_name)
            input_bucket = s3.Bucket(input_bucket_name)
            s3.Bucket(input_bucket_name).download_file(image_name, image_name)

            # Run the deep learning model on the image
            subprocess.run(['python3', pathlib.Path(__file__).parent.parent.parent.absolute() / "home/ubuntu/image_classification.py", image_name])

            # Read the result from the output file
            with open('output.txt', 'r') as f:
                result = f.read().strip()
            
            print(result)

            # Upload the result to S3
            file_to_store = '{}_Result.txt'.format(image_name)
            s3write = open(file_to_store, "w+")
            s3write.write(result)
            s3write.close()

            s3_client.upload_file(file_to_store, output_bucket_name, file_to_store)
            print('uploaded')

            # Send a message to the web tier with results from image recognition
            res_message = {str(image_name): result.split(',')[1]}
            sqs_message = sqs.Queue(response_queue_url).send_message(MessageBody=json.dumps(res_message))

            print(json.dumps(res_message))

            # Delete the message from the queue
            message.delete()