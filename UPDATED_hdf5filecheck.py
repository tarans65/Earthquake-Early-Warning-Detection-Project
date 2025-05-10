import h5py
with h5py.File("mqtt_data.h5", "r") as f:
    dset = f["mqtt_data"]
    print("Stored messages:")
    for i in range(dset.shape[0]):
        print(f"Message {i+1}: {dset[i].decode()}")
