from flask import Flask, Response
 
app = Flask(__name__)
data = ""
def on_message(client, userdata, message):
    global data
    data = message.payload.decode()
    print(data)
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect("vcm-47020.vm.duke.edu", 1883)
mqtt_client.subscribe("test")
mqtt_client.loop_start()
def start_mqtt_loop():
    mqtt_client.loop_forever()
# Start MQTT loop in a separate thread
mqtt_thread = threading.Thread(target=start_mqtt_loop)
mqtt_thread.daemon = True  # Allow thread to exit when the main program exits
mqtt_thread.start()
# Stream route for Flask to push real-time data to client
# @app.route('/stream')
# def stream():
#     def generate():
#         while True:
#             yield f"data: {data}\n\n"
#     return Response(generate(), mimetype="text/event-stream")
# Main Flask app runner
if __name__ == "__main__":
    app.run(debug=True, threaded=True)
