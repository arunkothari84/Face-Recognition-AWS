from flask import Flask, request
import os
import pandas as pd
import concurrent.futures

app = Flask(__name__)

df = pd.read_csv('/home/ubuntu/app/data.csv') # Change this to your data.csv path

def process_image(filename):
    file = os.path.splitext(filename.filename)[0]
    prediction = df[df['Image']==file]["Result"].item()
    response = "{}:{}".format(file, prediction)
    return response

@app.route("/", methods=["POST"])
def upload_image():
    if "inputFile" not in request.files:
        return "No file uploaded", 400

    file = request.files["inputFile"]

    if file.filename == "":
        return "No file selected", 400

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(process_image, file)
        prediction_result = future.result()

    return prediction_result, 200

if __name__ == "__main__":
    app.run(threaded=True, debug=True)