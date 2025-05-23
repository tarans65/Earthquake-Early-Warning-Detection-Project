import paho.mqtt.client as mqtt
import h5py
import time
import numpy as np
# HDF5 file to store data
hdf5_file = "mqtt_data.h5"
# Initialize the HDF5 file and create a resizable dataset
with h5py.File(hdf5_file, "a") as f:
    if "mqtt_data" not in f:
        # Create an empty, resizable dataset for strings
        dset = f.create_dataset("mqtt_data", (0,), maxshape=(None,), dtype=h5py.string_dtype())
        print("Dataset created.")
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("#")
def on_message(client, userdata, msg):
    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    with h5py.File(hdf5_file, "a") as f:
        dset = f["mqtt_data"]
        # Append the new message at the end of the dataset
        message = msg.payload.decode()
        # Check the current size and append correctly
        new_size = dset.shape[0] + 1
        dset.resize((new_size,))
        dset[-1] = message
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("vcm-47020.vm.duke.edu", 1883)
client.loop_forever()









