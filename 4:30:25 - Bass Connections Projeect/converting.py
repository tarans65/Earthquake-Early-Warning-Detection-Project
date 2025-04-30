import h5py
import pandas as pd
import sys

fpath = "mqtt_data.h5"

with h5py.File(fpath, "r") as f:
    if "mqtt_data" in f:
        data = list(f["mqtt_data"][:])  # Read all messages
    else:
        print("Dataset 'mqtt_data' not found in HDF5 file.")
        sys.exit(1)

# Convert bytes to strings if needed
data = [msg.decode() if isinstance(msg, bytes) else msg for msg in data]
# Create a DataFrame with one column
df = pd.DataFrame(data, columns=["message"])
# Save to CSV
df.to_csv("testing.csv", index=False)