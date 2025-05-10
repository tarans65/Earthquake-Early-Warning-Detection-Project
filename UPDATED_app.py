from flask import Flask, Response, request, send_file, jsonify
import pandas as pd
import h5py
from io import StringIO
from datetime import datetime
from flask import render_template


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stream")
def stream():
    def event_stream():
        with h5py.File("mqtt_data.h5", "r") as f:
            dset = f["mqtt_data"]
            last_index = dset.shape[0]
        while True:
            with h5py.File("mqtt_data.h5", "r") as f:
                dset = f["mqtt_data"]
                if dset.shape[0] > last_index:
                    new_msg = dset[last_index].decode()
                    yield f"data: {new_msg}\n\n"
                    last_index += 1
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
    df = read_and_filter_data(start, end)
    # Extract time and value (assumes comma-separated msg format: time,value)
    timestamps = []
    values = []
    for row in df["message"]:
        try:
            time_str, value_str = row.split(",")
            timestamps.append(time_str)
            values.append(float(value_str))
        except:
            continue
    return jsonify({"timestamps": timestamps, "values": values})

def read_and_filter_data(start, end):
    with h5py.File("mqtt_data.h5", "r") as f:
        if "mqtt_data" not in f:
            return pd.DataFrame(columns=["message"])
        data = [msg.decode() for msg in f["mqtt_data"][:]]
    df = pd.DataFrame(data, columns=["message"])
    # Optional: parse timestamp and filter (assumes timestamp,value format)
    if start and end:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        def in_range(msg):
            try:
                ts = datetime.fromisoformat(msg.split(",")[0])
                return start_dt <= ts <= end_dt
            except:
                return False
        df = df[df["message"].apply(in_range)]
    return df
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
