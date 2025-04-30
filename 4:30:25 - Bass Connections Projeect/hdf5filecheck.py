import h5py

# Open the HDF5 file in read mode
with h5py.File("mqtt_data.h5", "r") as f:
    dset = f["mqtt_data"]  # Access the "mqtt_data" dataset
    print("Stored messages:")
    
    # Loop through each message in the dataset and print it
    for i in range(dset.shape[0]):
        print(f"Message {i+1}: {dset[i].decode()}")