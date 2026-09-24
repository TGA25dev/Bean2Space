import serial
import time
import time 
import csv
from datetime import datetime

COM_PORT = 'COM5'
BAUD_RATE = 115200

csv_fields = [
    "timestamp", "packet_type", "sequence_number", "rssi",
    "flight_state", "flight_id",
    "temperature", "absolute_pressure", "relative_pressure",
    "altitude", "accel_x", "accel_y", "accel_z",
    "gyro_x", "gyro_y", "gyro_z", "temp_imu", "message",
]

def create_csv_writer(file):
    writer = csv.DictWriter(file, fieldnames=csv_fields)
    writer.writeheader()
    return writer

def write_packet_to_csv(writer, csv_file, packet):
    row = {field: "" for field in csv_fields}
    row.update(packet["header"])
    row.update(packet["payload"])

    writer.writerow(row)
    csv_file.flush()

print(f"Connecting to ground station on {COM_PORT}...")

def parse(line):
    try:
        parts = line.split(",")
        if len(parts) < 5:
            raise ValueError("Invalid packet format")

        timestamp = parts[0]
        packet_type = parts[1]
        sequence_number = int(parts[2])
        rssi = float(parts[3])
        flight_state = str(parts[4])
        flight_id = int(parts[5])

        base = {
            "timestamp": timestamp,
            "packet_type": packet_type,
            "sequence_number": sequence_number,
            "rssi": rssi,
            "flight_state": flight_state,
            "flight_id": flight_id
        }

        if packet_type == "telemetry": #temperature, absolute_pressure, relative_pressure, altitude, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp_imu

            payload = {
                "temperature": float(parts[6]),
                "absolute_pressure": float(parts[7]),
                "relative_pressure": float(parts[8]),
                "altitude": float(parts[9]),
                "accel_x": float(parts[10]),
                "accel_y": float(parts[11]),
                "accel_z": float(parts[12]),
                "gyro_x": float(parts[13]),
                "gyro_y": float(parts[14]),
                "gyro_z": float(parts[15]),
                "temp_imu": float(parts[16])
            }

            return {
                "header": base,
                "payload": payload
            }

        elif packet_type == "message": #message
            message = ",".join(parts[6:])

            return {
                "header": base,
                "payload": {
                    "message": message
                }
            }

        else:
            raise ValueError("Unknown packet type")

    except ValueError as e:
        print(f"Error parsing line: {line}. Error: {e}")
        return None
        

while True:
    try:
        current_time = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser, open(f"flights/{current_time}_flight_telemetry.csv", "a", newline="", encoding="utf-8") as csv_file:
            print("Connected! Listening for telemetry...")
            csv_writer = create_csv_writer(csv_file)
            
            while True:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        parsed_data = parse(line)
                        if parsed_data:
                            print(f"Received packet: {parsed_data["header"]["packet_type"]} with sequence number {parsed_data['header']['sequence_number']}")
                            write_packet_to_csv(csv_writer, csv_file, parsed_data)

    except (serial.SerialException, PermissionError):
        time.sleep(1) #if usb ever reboots it's handled