from flask import Flask, Response  
import paho.mqtt.client as mqtt   
import threading                  

app = Flask(__name__)  

data = ""  # Global variable to store the latest MQTT message

# Define callback for handling incoming MQTT messages
def on_message(client, userdata, message):
    global data
    data = message.payload.decode()  # decode the incoming message payload
    print(data)  

# Set up MQTT client and assign the on_message callback
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect("vcm-47020.vm.duke.edu", 1883)  # Connect to the MQTT broker
mqtt_client.subscribe("test")  # Subscribe to the "test" topic to receive messages
mqtt_client.loop_start()  # Start the MQTT client's loop to listen for messages

# Function to run the MQTT loop forever in a separate thread
def start_mqtt_loop():
    mqtt_client.loop_forever()

# Start MQTT loop in a separate thread so it doesn't block the Flask app
mqtt_thread = threading.Thread(target=start_mqtt_loop)
mqtt_thread.daemon = True  # Ensure the thread exits when the main program ends
mqtt_thread.start()

# Flask route to stream data to clients using Server-Sent Events (SSE)
@app.route('/stream')
def stream():
    def generate():
        while True:
            yield f"data: {data}\n\n"  # Stream the latest message to the client in SSE format
    return Response(generate(), mimetype="text/event-stream")  # Return a streaming response

# Main Flask app runner
if __name__ == "__main__":
    app.run(debug=True, threaded=True)  # Run the Flask app with debugging and multi-threading enabled