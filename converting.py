import h5py
import pandas as pd
import sys
fpath = "mqtt_data.h5"
# Open the HDF5 file and read the dataset
with h5py.File(fpath, "r") as f:
    # Check for the correct dataset key
    if "mqtt_data" in f:
        data = list(f["mqtt_data"][:])  # Read all data at once
    else:
        print("Dataset 'mqtt_data' not found in HDF5 file.")
        sys.exit(1)
# Convert bytes to strings (if necessary)
data = [msg.decode() if isinstance(msg, bytes) else msg for msg in data]
# Create a DataFrame from the list
df = pd.DataFrame(data, columns=["message"])
# Output as CSV
df.to_csv("testing.csv", index=False)