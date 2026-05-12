from flask import Flask, jsonify
from flask_cors import CORS
import serial
import re
from threading import Thread
import time
import os
import sys

app = Flask(__name__)
CORS(app)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "scale_agent_config.txt")

# ---------------- AUTO CREATE CONFIG ----------------
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        f.write("PORT=COM1\n")
        f.write("BAUDRATE=9600\n")
    print(f"Config file created at: {CONFIG_FILE}")

latest_weight = 0.0
serial_connected = False
active_port = "N/A"
active_baudrate = 0

# ---------------- CONFIG READER ----------------
def load_config():
    config = {"PORT": "COM1", "BAUDRATE": 9600}
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        config["BAUDRATE"] = int(config["BAUDRATE"])
    except Exception as e:
        print("Config read error:", e)
    return config

# ---------------- SERIAL THREAD ----------------
def serial_reader():
    global latest_weight, serial_connected, active_port, active_baudrate

    current_port = None
    current_baudrate = None
    ser = None

    while True:
        config = load_config()
        new_port = config["PORT"]
        new_baudrate = config["BAUDRATE"]

        if new_port != current_port or new_baudrate != current_baudrate:
            print(f"Config changed → PORT={new_port}, BAUDRATE={new_baudrate}")
            if ser and ser.is_open:
                ser.close()
            ser = None
            current_port = new_port
            current_baudrate = new_baudrate
            serial_connected = False

        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(
                    current_port,
                    baudrate=current_baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                serial_connected = True
                active_port = current_port
                active_baudrate = current_baudrate
                print(f"Serial connected on {current_port} at {current_baudrate}")
            except Exception as e:
                serial_connected = False
                active_port = current_port
                active_baudrate = current_baudrate
                print("Serial error:", e)
                time.sleep(2)
                continue

        try:
            line = ser.readline()
            text = line.decode("utf-8", errors="ignore").strip()
            match = re.search(r"(\d+(\.\d+)?)\s*KG", text)
            if match:
                latest_weight = float(match.group(1))
                print("Weight:", latest_weight)
            else:
                if text:
                    print("No match found in line:", text)
        except Exception as e:
            serial_connected = False
            print("Read error:", e)
            if ser and ser.is_open:
                ser.close()
            ser = None
            time.sleep(2)

# ---------------- API ----------------
@app.route("/read-weight")
def read_weight():
    return jsonify({
        "weight": latest_weight,
        "connected": serial_connected,
        "port": active_port,
        "baudrate": active_baudrate
    })

@app.route("/config")
def get_config():
    return jsonify(load_config())

# ---------------- MAIN ----------------
if __name__ == "__main__":
    Thread(target=serial_reader, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)