import time
import paho.mqtt.client as paho
#broker="broker.hivemq.com"
broker="169.234.25.41"
#define callback
def on_message(client, userdata, message):
    time.sleep(1)
    print("received message =",str(message.payload.decode("utf-8")))

client= paho.Client("client-001") #create client object client1.on_publish = on_publish #assign function to callback client1.connect(broker,port) #establish connection client1.publish("house/bulb1","on")
######Bind function to callback
client.on_message=on_message
#####
print("connecting to broker ",broker)
client.connect(broker)#connect
client.loop_start() #start loop to process received messages
print("subscribing ")
client.subscribe("house/bulb1")#subscribe
#client.subscribe("iot-1/d/b827eb3da2b9/evt/explosive_gas/json")#subscribe
client.subscribe("#")#subscribe
time.sleep(2000)
#print("publishing ")
#client.publish("house/bulb1","on")#publish
#client.publish("house/bulb1","off")#publish
#time.sleep(4)
#client.disconnect() #disconnect
#client.loop_stop() #stop loop
