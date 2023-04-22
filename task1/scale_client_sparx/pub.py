from config import *
# ZeroMQ Configuration
"""
ZMQ_HOST = '192.168.0.104'
ZMQ_PORT = '5554'
ZMQ_TOPICS = ["weather", "air"]

# Client folder name
folder_path = ['/home/pi/Desktop/data/weather', '/home/pi/Desktop/data/PMSensor']

wifi_name = "TP-LINK_1614"
SCAN_INTERVAL_SEC = 10
RETRY_INTERVAL_SEC = 20"""

import zmq
import os
import time
import subprocess

context = zmq.Context()

# create a ZMQ PUB socket
socket = context.socket(zmq.PUB)
socket.connect(f"tcp://{ZMQ_HOST}:{ZMQ_PORT}")

# set the topic for this publisher



def conn_check() -> bool:
    # Run the command to get the SSID of the currently connected network
    result = subprocess.run(['iwgetid', '-r'],shell = True, capture_output=True, text=True)

    # Extract the SSID from the output
    ssid = result.stdout.strip()

    # Check if the SSID is empty
    if not ssid:
        print("Not currently connected to a WiFi network")
        return False
    else:
        print(f"Currently connected to WIFI with ssid: {ssid}")
        return ssid == wifi_name

while True:
    if not conn_check():
        time.sleep(RETRY_INTERVAL_SEC)
        continue
    # scan the folder and upload all files with the given topic
    for i in range(0,2):
        topic = ZMQ_TOPICS[i]
        for filename in os.listdir(folder_path[i]):
            filepath = os.path.join(folder_path[i], filename)
            with open(filepath, "rb") as f:
                data = f.read()

            try:
                # send the data to the subscriber with the given topic
                socket.send_multipart([topic.encode(), filename.encode(), data])
                print(f"Published {filename} on topic {topic}")
            except zmq.ZMQError as e:
                print(f"Error: {e}, retrying in 5 seconds")
                time.sleep(RETRY_INTERVAL_SEC)
                break

            os.remove(filepath)

    time.sleep(SCAN_INTERVAL_SEC)
