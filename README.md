# KTMGeoLab: Real-Time Seismic Monitoring Platform

This website is a real-time earthquake monitoring system built to stream, store, visualize, and analyze seismic data collected from an Arduino-based geophone sensor. The platform is designed for local deployment in Kathmandu and enables users to observe live seismic trends, filter data by time, and download earthquake sensor data as CSV files.

---

## 🌐 Features

- 🔄 **Live Data Streaming** from MQTT-connected Arduino sensors
- 📁 **HDF5-Based Data Storage** for efficient time-series management
- 📊 **Interactive Data Visualization** (X, Y, Z axis readings vs time)
- ⏳ **Time-Based Filtering** for historical insights
- 📥 **CSV Export** of filtered seismic data
- 🚦 Robust back-end powered by **Flask**, **paho-mqtt**, and **Plotly**

---

---

## ⚙️ How It Works

1. **Sensor** publishes seismic data to an MQTT broker under the topic `geophone/data`.
2. **Flask server** subscribes to this topic using `paho.mqtt.client`.
3. Each message is parsed and:
   - Stored in memory for real-time streaming.
   - Queued and written in batches to an HDF5 file using a thread-safe system.
4. Users interact with the frontend to:
   - Stream recent data (`/stream`)
   - Filter by start/end time and axis (`/filtered-data`)
   - Download filtered CSVs (`/download`)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- MQTT broker (e.g. Mosquitto)
- Arduino geophone sensor publishing to topic `geophone/data`

### Install Dependencies

```bash
pip install flask pandas h5py paho-mqtt

Run the Server
python3 app.py

Message Structure:
X:-1.031, Y:-1.030, Z:-1.029, ReadTime:08:29:49.0875, OutputTime:08:29:49.0875

