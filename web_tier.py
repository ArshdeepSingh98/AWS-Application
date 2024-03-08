"""
    This code uses the Flask framework to create a web server that listens for image files posted to the /image endpoint. 
    When an image file is received, it uploads the file to the input S3 bucket and sends a message to the app tier through SQS. 
    The response to the user is a JSON object containing the SQS message ID.

    We will need to customize this code to match the specifics, such as the names of the S3 buckets and SQS queue, and the endpoint for the app tier.
    Execute:
    tmux attach -t mytestapp
    python web_tier
"""
import boto3
from flask import Flask, request, jsonify
import requests
import json
import os
import pathlib
import yaml
from threading import Thread, Semaphore, Barrier

# Create a new Flask app
app = Flask(__name__)

# Set up credentials
settings_path = pathlib.Path(__file__).parent.parent.parent.absolute() / "ubuntu/web_tier" / "settings.yaml"
with open(settings_path, "r") as infile:
    CONFIG = yaml.safe_load(infile)

# Put some credentials in the environment
os.environ["AWS_ACCESS_KEY_ID"] = CONFIG["aws_settings"]["AWSAccessKeyID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = CONFIG["aws_settings"]["AWSSecretAccessKey"]
os.environ["AWS_DEFAULT_REGION"] = CONFIG["aws_settings"]["AWSDefaultRegion"]

# Set up the AWS clients
s3 = boto3.client('s3', region_name='us-east-1')
sqs = boto3.resource('sqs', region_name='us-east-1')
sqs_client = boto3.client('sqs', region_name='us-east-1')
ec2 = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

request_queue_name = 'requestQueue'
request_queue_url = sqs.get_queue_by_name(QueueName=request_queue_name).url
response_queue_name = 'responseQueue'
response_queue_url = sqs.get_queue_by_name(QueueName=response_queue_name).url
response_queue = sqs.get_queue_by_name(QueueName='responseQueue')

# Define the endpoint for the app tier
app_tier_endpoint = 'http://app-tier-lb-1234567890.us-east-1.elb.amazonaws.com'

# Define the S3 bucket names for inputs and outputs
input_bucket_name = 'inputbucket546'
output_bucket_name = 'outputbucket546'

results = {}
auto_scale_flag = True
MAX_APP_TIERS = 20

def create_instance(min_count=1, max_count=19):
    for i in range(max_count):
        instance_name = f'app-instance-{i+1}'
        response = ec2_client.run_instances(
            ImageId=CONFIG["aws_settings"]['ImageId'],
            InstanceType=CONFIG["aws_settings"]['InstanceType'],
            KeyName=CONFIG["aws_settings"]['KeyName'],
            SecurityGroupIds=['sg-0a8735f7fe32f271b'],
            SubnetId='subnet-00f42621c31d7f72d',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': instance_name
                        },
                    ]
                },
            ],
            MinCount=1,
            MaxCount=1
        )
        print(f'Instance {instance_name} created with ID {response["Instances"][0]["InstanceId"]}')

def autoscale():
    #get length of queue with url given, which denotes the number of req on the SQS
    queue_approx_num_msgs=sqs_client.get_queue_attributes(
        QueueUrl=request_queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    
    #convert to integer
    queue_len=int(queue_approx_num_msgs['Attributes']['ApproximateNumberOfMessages'])

    # create filter for instances in running state
    filters = [
        {
            'Name': 'instance-state-name', 
            'Values': ['running']
        }
    ]
    
    # filter the instances based on filters() above
    instances = ec2.instances.filter(Filters=filters)

    # instantiate empty array
    RunningInstances = []

    for instance in instances:
        # for each instance, append to array and print instance id
        RunningInstances.append(instance.id)
       # print instance.id
    i_len= len(RunningInstances)
    #launch 20-number of running instances
    max_ec2_launch=MAX_APP_TIERS-i_len
    #take the minimum of number of requests and value calculated above
    num_ec2_launch=min(queue_len,max_ec2_launch)

    #create as many instances as calculated
    if(i_len <= 5):    
        create_instance(1,19)

def listen_for_results():
    while True:
        messages = response_queue.receive_messages()
        if messages:
            # Process each message
            for message in messages:
                print(message.body)
                message_dict = eval(message.body) # Convert string to dictionary
                fwrite = open('Results.txt', "a+")
                fwrite.write(str(message.body)+"\n")
                fwrite.close()

                # Extract the key-value pairs from the message body and add them to the dictionary
                for key, value in message_dict.items():
                    results[key] = value
                # Delete the message from the queue
                message.delete()
            return

# Route for receiving images from users
@app.route('/image', methods=['POST'])
def receive_image():
    global auto_scale_flag
    # Get the image file from the request
    image_file = request.files['myfile']

    # Generate a unique filename for the image
    image_filename = str(image_file.filename)

    # Upload the image file to the input S3 bucket
    s3.put_object(Bucket=input_bucket_name, Key=image_filename, Body=image_file)

    # Send a message to the app tier to request image recognition
    message = {'image_filename': image_filename}
    sqs_message = sqs.Queue(request_queue_url).send_message(MessageBody=json.dumps(message))

    if(auto_scale_flag):
        # Autoscaled via cloudwatch and ASG
        #autoscale()
        auto_scale_flag = False

    listen_for_results()

    # Return the message ID as confirmation
    return json.dumps(results), 200

# Main function to run the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)