

from flask import Flask, request
import os
import boto3
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import tempfile
import json

request_queue_url = # Add your request queue url here
response_queue_url = # Add your response queue url here
S3_intput = # Add your input bucket name here
S3_output = # Add your output bucket name here


app = Flask(__name__)

ec2 = boto3.client('ec2')
sqs = boto3.client('sqs')
s3 = boto3.client('s3')
num_messages = 0
num_messages_lock = threading.Lock()
all_messages = {}
all_messages_lock = threading.Lock()


#Cleaning everything
objects = s3.list_objects_v2(Bucket=S3_intput)
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3.delete_object(Bucket=S3_intput, Key=obj['Key'])

objects = s3.list_objects_v2(Bucket=S3_output)
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3.delete_object(Bucket=S3_output, Key=obj['Key'])

sqs.purge_queue(QueueUrl=request_queue_url)
sqs.purge_queue(QueueUrl=response_queue_url)
    
# Done!

def fetchAllMessages():
    global all_messages
    print("Checking Messages!")
    while True:
        with all_messages_lock:
            messages = sqs.receive_message(
                QueueUrl=response_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
            )
            if 'Messages' in messages:
                message = json.loads(messages['Messages'][0]['Body'])
                key = message['key'] # Key of the ouput is the image name
                object_data = s3.get_object(Bucket=S3_output, Key=key)
                prediction = object_data['Body'].read().decode('utf-8')
                
                sqs.delete_message(
                    QueueUrl=response_queue_url,
                    ReceiptHandle=messages['Messages'][0]['ReceiptHandle']
                )
                all_messages[key] = prediction

        time.sleep(2)
        

def adjust_asg_capacity():
    global num_messages
    while True:
        with num_messages_lock:
            if num_messages > 10:
                desired_capacity = 20
            else:
                desired_capacity = num_messages if num_messages > 0 else 0

        if desired_capacity > 0:
            response = ec2.run_instances(
                        LaunchTemplate={
                            'LaunchTemplateName': 'App-Tier-Project-1-Part-2',
                            'Version': "8"
                        },
                        MinCount=1,
                        MaxCount=desired_capacity,
                        TagSpecifications=[
                            {
                                'ResourceType': 'instance',
                                'Tags': [
                                    {
                                        'Key': 'Name',
                                        'Value': f'app-tier-*'
                                    }
                                ]
                            }
                        ]
                        )
            desired_capacity = 0
            num_messages = 0
        time.sleep(2)

def fetchFromOutputBucket(filename):
    # global num_messages
    global all_messages
    while True:
        with all_messages_lock:
            if filename.split('.')[0] in all_messages.keys():
                response = "{}:{}".format(filename.split('.')[0], all_messages[filename.split('.')[0]])
                # print("Step UP:",response)
                del all_messages[filename.split('.')[0]]
                return response

        time.sleep(2)


asg_thread = threading.Thread(target=adjust_asg_capacity)
asg_thread.start()

fetchAllMessages_thread = threading.Thread(target=fetchAllMessages)
fetchAllMessages_thread.start()

executor = ThreadPoolExecutor(max_workers=10)

@app.route('/', methods=['GET'])
def block_get_request():
    return ""

@app.route('/', methods=['POST'])
def upload_files():
    global num_messages

    file = request.files["inputFile"]
    filename = file.filename
    
    if filename != "":
        with num_messages_lock:
            num_messages += 1

        
        message_attribute_filter = {
        'filename': {
            'DataType': 'String',
            'StringValue': filename
        }
        }

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        file.save(temp_file_path)
        # Upload on S3 Input bucket and get key and store in key
        key = s3.upload_file(temp_file_path, S3_intput, filename)

        os.remove(temp_file_path)

        sqs.send_message(
        QueueUrl=request_queue_url,
        MessageBody=json.dumps({"filename": filename})
        )

        
        future_Bucket = executor.submit(fetchFromOutputBucket, filename)
        prediction_result = future_Bucket.result()
        print("returting", prediction_result)

        return prediction_result, 200

if __name__ == "__main__":
    app.run(threaded=True)