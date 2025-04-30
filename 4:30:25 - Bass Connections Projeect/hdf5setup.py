import paho.mqtt.client as mqtt  
import h5py                    
import time                  
import numpy as np               

# HDF5 file to store MQTT data
hdf5_file = "mqtt_data.h5"

# Initialize the HDF5 file and create a resizable dataset if it doesn't exist
with h5py.File(hdf5_file, "a") as f:
    if "mqtt_data" not in f:
        # Create an empty, resizable dataset for storing messages as strings
        dset = f.create_dataset("mqtt_data", (0,), maxshape=(None,), dtype=h5py.string_dtype())
        print("Dataset created.")

# Callback for when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("test")  # Subscribe to the "test" topic

# Callback for when a message is received on the subscribed topic
def on_message(client, userdata, msg):
    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    
    # Open the HDF5 file to append the new message
    with h5py.File(hdf5_file, "a") as f:
        dset = f["mqtt_data"]
        message = msg.payload.decode()  # Decode the message payload
        
        # Resize the dataset and append the new message
        new_size = dset.shape[0] + 1
        dset.resize((new_size,))
        dset[-1] = message  # Store the new message at the end of the dataset

# Set up the MQTT client and assign the callbacks
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker and start listening for messages
client.connect("vcm-47020.vm.duke.edu", 1883)
client.loop_forever()  # Start the infinite loop to process incoming messages