import torch
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
import boto3
import json
from dotenv import load_dotenv
import asyncio

print("started!!")
load_dotenv()

sqs = boto3.client('sqs', region_name='us-east-1')  
s3 = boto3.client('s3', region_name='us-east-1')

# Define your SQS queue URLs
request_queue_url = # Change this to your request queue URL
response_queue_url = # Change this to your response queue URL

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion

def face_match(img_path): # img_path= location of photo, data_path= location of data.pt
    # getting embedding matrix of the given img
    img = Image.open(img_path)
    face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false

    saved_data = torch.load('data.pt') # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person

    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))



async def setIntervalPooling():
    print("Running Loop!!!")
    while True:
        data = sqs.receive_message(
                QueueUrl=request_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5
            )
        # print(data)
        if 'Messages' in data:
            message = json.loads(data['Messages'][0]['Body'])
            S3_intput = '1229515081-in-bucket'
            S3_output = "1229515081-out-bucket"

            local_file_path = '/home/ubuntu/model/images/image.jpg'

            recepitHandle = data['Messages'][0]['ReceiptHandle']

            filename = message['filename']

            message_attributes = {
                'filename': {
                    'DataType': 'String',
                    'StringValue': filename
                }
            }

            s3.download_file(S3_intput, filename, local_file_path)

            result = face_match(local_file_path, 'data.pt')

            if result:
                key=filename.split('.')[0]
                S3Outputkey = s3.put_object(Bucket=S3_output, Key=key, Body=result[0])
                # print(S3Outputkey)
                
                sqs.send_message(
                    QueueUrl=response_queue_url,
                    MessageAttributes=message_attributes,
                    MessageBody=json.dumps({"key":key})
                )
                
                # s3.delete_object(Bucket=S3_intput, Key=filename)
                deleteMessageRes = sqs.delete_message(
                            QueueUrl=request_queue_url,
                            ReceiptHandle=recepitHandle)
                    #  print("deleted: ", deleteMessageRes['ResponseMetadata']['HTTPStatusCode'])
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(setIntervalPooling())
