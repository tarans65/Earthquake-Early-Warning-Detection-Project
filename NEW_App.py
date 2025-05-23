from flask import Flask, Response, request, send_file, jsonify, render_template
import pandas as pd
import h5py
from io import StringIO
from datetime import datetime
import threading
import paho.mqtt.client as mqtt
import time
import queue
import fcntl
import os

app = Flask(__name__)

# Use a queue to buffer MQTT messages and maintain an in-memory cache
mqtt_queue = queue.Queue()
message_cache = []
cache_lock = threading.Lock()
shutdown_event = threading.Event()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stream")
def stream():
    print("stream1")
    def event_stream():
        last_index = 0
        with cache_lock:
            last_index = len(message_cache)
            
        while True:
            with cache_lock:
                if len(message_cache) > last_index:
                    new_msg = message_cache[last_index]
                    print("stream3")
                    yield f"data: {new_msg}\n\n"
                    last_index += 1
            time.sleep(0.1)  # Small delay to prevent excessive polling

    return Response(event_stream(), content_type="text/event-stream")

@app.route("/download")
def download():
    start = request.args.get("start")
    end = request.args.get("end")
    df = read_and_filter_data(start, end)
    csv = df.to_csv(index=False)
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=filtered_data.csv"}
    )

@app.route("/filtered-data")
def filtered_data():
    start = request.args.get("start")
    end = request.args.get("end")
    axis = request.args.get("axis", "X")  # Allow selecting which axis to plot (X, Y, or Z)
    
    df = read_and_filter_data(start, end)
    timestamps = []
    values = []
    
    for row in df["message"]:
        try:
            # Parse the data format: "X:0.000, Y:0.000, Z:0.000, ReadTime:07:44:58.0186, OutputTime:07:44:58.0186"
            parts = row.split(", ")
            
            # Extract values
            x_val = None
            y_val = None
            z_val = None
            read_time = None
            
            for part in parts:
                if part.startswith("X:"):
                    x_val = float(part.split(":")[1])
                elif part.startswith("Y:"):
                    y_val = float(part.split(":")[1])
                elif part.startswith("Z:"):
                    z_val = float(part.split(":")[1])
                elif part.startswith("ReadTime:"):
                    read_time = part.split(":", 1)[1]  # Use split with maxsplit=1 to handle time format
            
            # Use the selected axis value
            if axis == "X" and x_val is not None:
                values.append(x_val)
            elif axis == "Y" and y_val is not None:
                values.append(y_val)
            elif axis == "Z" and z_val is not None:
                values.append(z_val)
            else:
                continue  # Skip this row if we can't get the requested axis
            
            # Format timestamp for plotting
            if read_time:
                # Convert time format from HH:MM:SS.ssss to a full datetime
                today = datetime.now().strftime("%Y-%m-%d")
                full_timestamp = f"{today} {read_time}"
                
                # Handle the microseconds format - pad or truncate to 6 digits
                try:
                    # Parse and reformat the timestamp to handle microseconds properly
                    dt = datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    formatted_timestamp = dt.isoformat()
                    timestamps.append(formatted_timestamp)
                except ValueError:
                    # If parsing fails, try without microseconds
                    try:
                        dt = datetime.strptime(full_timestamp.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        timestamps.append(dt.isoformat())
                    except ValueError:
                        continue
            else:
                continue  # Skip if no valid timestamp
                
        except Exception as e:
            print(f"Error parsing row: {row}, Error: {e}")
            continue
    
    return jsonify({
        "timestamps": timestamps, 
        "values": values,
        "axis": axis,
        "count": len(values)
    })

def read_and_filter_data(start, end):
    # First try to read from cache for recent data
    with cache_lock:
        cache_data = message_cache.copy()
    
    # Then read from HDF5 file
    hdf5_data = []
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if os.path.exists("mqtt_data.h5"):
                with h5py.File("mqtt_data.h5", "r") as f:
                    if "mqtt_data" in f:
                        hdf5_data = [msg.decode() for msg in f["mqtt_data"][:]]
            break
        except (OSError, BlockingIOError) as e:
            print(f"Read attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            else:
                print("Using cache data only due to file access issues")
    
    # Combine HDF5 data with cache data (remove duplicates)
    all_data = hdf5_data + cache_data
    # Remove duplicates while preserving order
    seen = set()
    unique_data = []
    for item in all_data:
        if item not in seen:
            seen.add(item)
            unique_data.append(item)
    
    df = pd.DataFrame(unique_data, columns=["message"])
    
    if start and end:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        def in_range(msg):
            try:
                # Extract ReadTime from the message
                parts = msg.split(", ")
                for part in parts:
                    if part.startswith("ReadTime:"):
                        time_str = part.split(":", 1)[1]
                        # Create full datetime
                        today = datetime.now().strftime("%Y-%m-%d")
                        # Get date from user input
                        start_date_str = start.split("T")[0]
                        full_timestamp = f"{start_date_str} {time_str}"
                        
                        # Handle the microseconds format properly
                        try:
                            ts = datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            # If parsing with microseconds fails, try without
                            ts = datetime.strptime(full_timestamp.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        
                        return start_dt <= ts <= end_dt
                return False
            except Exception as e:
                print(f"Error filtering message: {e}")
                return False
        df = df[df["message"].apply(in_range)]
    return df

# MQTT handling - just queue the messages
def on_message(client, userdata, message):
    try:
        data = message.payload.decode()
        mqtt_queue.put(data)
        # Also add to cache immediately for real-time streaming
        with cache_lock:
            message_cache.append(data)
            # Keep cache size reasonable (last 1000 messages)
            if len(message_cache) > 1000:
                message_cache.pop(0)
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def safe_hdf5_write(data):
    """Safely write to HDF5 with proper error handling"""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            # Try to acquire a simple file-based lock
            lock_file = "mqtt_data.h5.lock"
            
            # Check if lock file exists and is old (cleanup stale locks)
            if os.path.exists(lock_file):
                lock_age = time.time() - os.path.getmtime(lock_file)
                if lock_age > 30:  # Remove locks older than 30 seconds
                    try:
                        os.remove(lock_file)
                    except:
                        pass
            
            # Try to create lock file atomically
            try:
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                lock_acquired = True
            except FileExistsError:
                lock_acquired = False
            
            if not lock_acquired:
                raise BlockingIOError("Could not acquire file lock")
            
            try:
                # Now safely write to HDF5
                with h5py.File("mqtt_data.h5", "a") as f:
                    if "mqtt_data" not in f:
                        maxshape = (None,)
                        dt = h5py.string_dtype(encoding="utf-8")
                        dset = f.create_dataset("mqtt_data", shape=(0,), maxshape=maxshape, dtype=dt)
                    else:
                        dset = f["mqtt_data"]
                    dset.resize((dset.shape[0] + 1,))
                    dset[-1] = data
                    f.flush()  # Force write to disk
                
                # Remove lock file
                try:
                    os.remove(lock_file)
                except:
                    pass
                return True
                
            except Exception as e:
                # Make sure to remove lock file even on error
                try:
                    os.remove(lock_file)
                except:
                    pass
                raise e
            
        except (OSError, BlockingIOError, IOError) as e:
            if attempt < max_attempts - 1:
                wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                time.sleep(wait_time)
            else:
                print(f"Failed to write after {max_attempts} attempts: {e}")
                return False
        except Exception as e:
            print(f"Unexpected error during HDF5 write: {e}")
            return False
    return False

def hdf5_writer_thread():
    """Single thread responsible for writing to HDF5 file"""
    batch = []
    batch_size = 10
    last_write = time.time()
    
    while not shutdown_event.is_set():
        try:
            # Collect messages in batches for efficiency
            try:
                data = mqtt_queue.get(timeout=1.0)
                batch.append(data)
                mqtt_queue.task_done()
            except queue.Empty:
                pass
            
            # Write batch if it's full or if enough time has passed
            current_time = time.time()
            if (len(batch) >= batch_size) or (batch and (current_time - last_write) > 5.0):
                # Write all messages in batch
                for msg in batch:
                    if not safe_hdf5_write(msg):
                        print(f"Failed to write message to HDF5: {msg[:50]}...")
                batch.clear()
                last_write = current_time
                
        except Exception as e:
            print(f"Error in HDF5 writer thread: {e}")
            time.sleep(1)
    
    # Write any remaining messages before shutdown
    if batch:
        for msg in batch:
            safe_hdf5_write(msg)

def safe_hdf5_read():
    """Safely read from HDF5 with file locking"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if not os.path.exists("mqtt_data.h5"):
                return []
                
            with h5py.File("mqtt_data.h5", "r") as f:
                if "mqtt_data" not in f:
                    return []
                data = [msg.decode() for msg in f["mqtt_data"][:]]
            return data
            
        except (OSError, BlockingIOError) as e:
            print(f"HDF5 read attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(0.1 * (attempt + 1))
        except Exception as e:
            print(f"Unexpected error during HDF5 read: {e}")
            break
    return []

# MQTT setup
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
mqtt_client.on_message = on_message

def start_mqtt():
    try:
        mqtt_client.connect("vcm-47020.vm.duke.edu", 1883, 60)
        mqtt_client.subscribe("geophone/data")
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"MQTT connection error: {e}")
        time.sleep(5)

# Start threads
writer_thread = threading.Thread(target=hdf5_writer_thread)
writer_thread.daemon = True
writer_thread.start()

mqtt_thread = threading.Thread(target=start_mqtt)
mqtt_thread.daemon = True
mqtt_thread.start()

# Cleanup function
def cleanup():
    shutdown_event.set()
    try:
        mqtt_client.disconnect()
    except:
        pass
    try:
        os.remove("mqtt_data.h5.lock")
    except:
        pass

import atexit
atexit.register(cleanup)

if __name__ == "__main__":
    try:
        app.run(debug=True, host="0.0.0.0")
    finally:
        cleanup()
