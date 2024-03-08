"""
    Design to CloudWatch to scale EC2 instances based on the size of an SQS queue:
    1. Create an Amazon CloudWatch alarm for the SQS queue. This alarm should be based on the "ApproximateNumberOfMessagesVisible" metric,
        which gives the number of messages that are currently visible in the queue.
        Set the threshold for the alarm based on the desired scaling behavior. For example, you might set the alarm threshold to 100 messages,
        so that the alarm is triggered whenever the queue size exceeds this number.
    2. Create a new Amazon EC2 Auto Scaling group for your application instances. This group should have a launch configuration that specifies the AMI and
        instance type that you want to use for your instances.
        You can also specify any other configuration details that you need for your instances, such as security groups or IAM roles.
    3. Configure the Auto Scaling group to use the CloudWatch alarm that you created in step 1. 
        You can do this by adding the alarm as a scaling policy for the group. When the alarm is triggered, the scaling policy will be activated,
        and the Auto Scaling group will launch new instances to handle the increased load.
    4. Set the desired capacity for the Auto Scaling group. This is the number of instances that you want to have running at any given time.
        You can set this value based on the expected demand for your application, or you can use other factors to determine the appropriate capacity level.
    5. Monitor the SQS queue and adjust the desired capacity of the Auto Scaling group as needed. 
        You can do this manually, or you can use automation tools such as AWS Lambda functions to adjust the capacity automatically based on the queue size.
"""

import boto3
import time

# Set up the client and resource for EC2 and SQS
ec2_client = boto3.client('ec2')
ec2_resource = boto3.resource('ec2')
sqs_client = boto3.client('sqs')
sqs_resource = boto3.resource('sqs')

# Set up the autoscaling group
asg_client = boto3.client('autoscaling')
asg_group_name = 'my-autoscaling-group'
min_instances = 1
max_instances = 20

# Set up the SQS queue
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue'
queue = sqs_resource.Queue(queue_url)

# Set up the CloudWatch alarms
alarm_name = 'my-alarm'
metric_name = 'ApproximateNumberOfMessagesVisible'
namespace = 'AWS/SQS'
comparison_operator = 'GreaterThanThreshold'
threshold = 5
evaluation_periods = 1
period = 60
actions_enabled = True
autoscaling_policy_name = 'my-scaling-policy'

"""
Requirement:
The max scale up number of instances should be 20. If the requests are less than 20, then the number of ec2 instances should be almost the number of requests in the queue.
However, if the requests are more than 20, then the auto scaling should maintain max count of instances to be 20, it should not exceed that threshold.
"""

# Replace with AWS account values
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/request_queue'
autoscaling_group_name = 'app-tier-autoscaling-group'

sqs = boto3.client('sqs')
autoscaling = boto3.client('autoscaling')
ec2 = boto3.client('ec2')

def get_queue_size(queue_url):
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes']['ApproximateNumberOfMessages'])

def get_instance_count():
    response = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[autoscaling_group_name],
        MaxRecords=1
    )
    return len(response['AutoScalingGroups'][0]['Instances'])

def set_instance_count(count):
    autoscaling.set_desired_capacity(
        AutoScalingGroupName=autoscaling_group_name,
        DesiredCapacity=count
    )

def scale():
    queue_size = get_queue_size(queue_url)
    instance_count = get_instance_count()
    if queue_size > 0:
        new_instance_count = min(queue_size, 20)
        if new_instance_count > instance_count:
            set_instance_count(new_instance_count)
    else:
        if instance_count > 1:
            set_instance_count(1)
        elif instance_count == 1:
            # Check if instance is idle for 10 minutes
            reservations = ec2.describe_instances(Filters=[
                {'Name': 'tag:Name', 'Values': ['app-instance*']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ])['Reservations']
            instance_ids = []
            for reservation in reservations:
                for instance in reservation['Instances']:
                    if (time.time() - instance['LaunchTime'].timestamp()) > 600:
                        instance_ids.append(instance['InstanceId'])
            if len(instance_ids) > 0:
                autoscaling.terminate_instance_in_auto_scaling_group(
                    InstanceIds=instance_ids,
                    ShouldDecrementDesiredCapacity=True
                )

if __name__ == '__main__':
    while True:
        scale()
        time.sleep(60)
