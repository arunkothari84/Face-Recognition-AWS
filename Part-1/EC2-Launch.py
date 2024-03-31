from decouple import config
import boto3

# This is to create a new EC2 instance
ec2 = boto3.resource(
      'ec2', 
      region_name='us-east-1',
      aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'))


ami_id = "ami-00ddb0e5626798373" # Change this to your AMI ID
key_pair_name = 'Cloud-Computing-S24' # Change this to your key pair name

# REVIEW: This is to create and run instance 
# WATCH: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/service-resource/create_instances.html

instance = ec2.create_instances(
           ImageId=ami_id,
           MinCount=1,
           MaxCount=1,
           InstanceType="t2.micro",
           KeyName=key_pair_name,
           TagSpecifications=[{'ResourceType':'instance',
                               'Tags': [{
                                'Key': 'Name',
                                'Value': 'web-instance' }]}]# REVIEW: To copy from already created SecurityGroup
                                )

print(instance)