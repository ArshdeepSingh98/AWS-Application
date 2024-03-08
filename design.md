To meet the requirements outlined, the following steps can be taken:

    Set up the AWS environment:
        Create two buckets in S3: one for inputs and one for outputs.
        Create an SQS queue for storing the incoming requests.
        Create an Elastic Load Balancer (ELB) and attach it to an auto-scaling group of EC2 instances for the app tier.
        Create a Launch Configuration for the app tier instances, specifying the AMI ID and other configurations such as instance type, security group, key pair, etc.
        Configure CloudWatch alarms to trigger scaling policies for the auto-scaling group based on the depth of the Request SQS Queue.
        Create an IAM role for EC2 instances to access the S3 bucket and the SQS queue.

    Develop the image recognition app:
        Write a script to handle the image recognition task using the provided deep learning model.
        When a request is received, the app should first retrieve the image from the input S3 bucket.
        The app should then perform the image recognition task and generate the recognition result.
        The result should be saved to the output S3 bucket with the same image name but a different file extension.
        Finally, the result should be returned to the user.

    Deploy the app:
        Upload the image recognition script to the app-tier instances.
        Configure the ELB to distribute incoming requests across the app-tier instances.
        Test the app with the workload generator.

    Monitor and scale the app:
        Monitor the app's performance and resource utilization using CloudWatch metrics.
        If the app is not meeting the performance requirements, adjust the scaling policies or the instance configurations.
        If the app is exceeding the limit of 20 instances, queue all the pending requests.
        If the app is not receiving any requests, use the minimum number of instances (1 instance in the APP tier).

    Document the app:
        Document the app's architecture, components, and deployment process in the README file.
        Include instructions for setting up the AWS environment, deploying the app, and testing it with the workload generator.
        Provide examples of input and output files in the input and output S3 buckets.