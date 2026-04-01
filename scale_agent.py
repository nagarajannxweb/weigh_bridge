from flask import Flask, jsonify
from flask_cors import CORS
import serial
import re
from threading import Thread
import time

app = Flask(__name__)
CORS(app)

PORT = "COM1"
BAUDRATE = 9600

latest_weight = 0.0
serial_connected = False


# ---------------- SERIAL THREAD ----------------
def serial_reader():
    global latest_weight, serial_connected

    while True:
        try:
            ser = serial.Serial(
                PORT,
                baudrate=BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )

            serial_connected = True
            print("Serial connected")

            while True:
                line = ser.readline()
                text = line.decode("utf-8", errors="ignore").strip()

                match = re.search(r"(\d+(\.\d+)?)\s*KG", text)
                if match:
                    latest_weight = float(match.group(1))
                    print("Weight:", latest_weight)
                else:
                    print("No match found in line:", text)

        except Exception as e:
            serial_connected = False
            print("Serial error:", e)
            time.sleep(2)   # retry


# ---------------- API ----------------
@app.route("/read-weight")
def read_weight():
    return jsonify({
        # "weight": latest_weight,
        "weight": 10,
        "connected": serial_connected
    })


# ---------------- MAIN ----------------
if __name__ == "__main__":
    Thread(target=serial_reader, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
