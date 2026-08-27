import espnow #type: ignore
import network
import wifi
import time

time.sleep(3)

print("\n" + "="*40)
print("SYSTEM BOOT: ground station started!")
print("="*40 + "\n")

wifi.reset(sta=True, ap=False, channel=6) #start wifi in station mode (channel 6) and disable AP mode

wlan = network.WLAN(network.STA_IF)
wlan.config(protocol=network.MODE_LR) #type: ignore #enable LR Mode

print("Ground station MAC:", wlan.config("mac"))
print("Ground station Wi-Fi channel:", wlan.config("channel"))

receiver = espnow.ESPNow()
receiver.active(True)

#create a pre allocated storage list to grab the RSSI
telemetry_packet = [bytearray(6), bytearray(250), 0, 0] # [mac_address, message_buffer, rssi, timestamp]

print("Ground Stations is active! Waiting for telemetry packets...")

last_telemetry_sequence = None
last_message_sequence = None

while True:
    #check if a packet is waiting in the radio stack
    if receiver.any():
        try:
            # recvinto extracts data directly into the list, captures RSSI automatically
            length = receiver.recvinto(telemetry_packet)
            
            if length > 0:
                #extract components from our pre allocated list :
                sender_mac = telemetry_packet[0]
                raw_msg = telemetry_packet[1][:length] #trim buffer to the true message length
                rssi = telemetry_packet[2]             #signal strength in dBm
                
                #decode and print data payload
                data_payload = raw_msg.decode('utf-8')

                try:
                    parts = data_payload.split(",")

                    timestamp = parts[0]
                    packet_type = parts[1]
                    sequence_number = int(parts[2])
                    flight_state = parts[3]
                    flight_id = parts[4]
                    sequence = sequence_number

                    if packet_type == "telemetry":
                        if len(parts) != 16:
                            raise ValueError("Invalid telemetry packet")

                        (
                            timestamp,
                            packet_type,
                            sequence_number,
                            flight_state,
                            flight_id,
                            temperature,
                            absolute_pressure,
                            relative_pressure,
                            altitude,
                            accel_x,
                            accel_y,
                            accel_z,
                            gyro_x,
                            gyro_y,
                            gyro_z,
                            temp_imu,
                        ) = parts

                        if last_telemetry_sequence is not None:
                            missing = sequence - last_telemetry_sequence - 1
                            
                            if missing > 0:
                                print(f"{missing} telemetry packets missing ! (last seq: {last_telemetry_sequence}, current seq: {sequence})")

                        last_telemetry_sequence = sequence

                        print(
                            f"Timestamp: {timestamp} | "
                            f"Telemetry Sequence: {sequence_number} | "
                            f"Flight ID: {flight_id} | "
                            f"State: {flight_state} | "
                            f"Temperature: {temperature}°C | "
                            f"Pressure: {absolute_pressure} Pa | "
                            f"Altitude: {altitude} m | "
                            f"Signal: {rssi} dBm")
                        
                    elif packet_type == "message":
                        if len(parts) < 6:
                            raise ValueError("Invalid message packet")

                        message = ",".join(parts[5:])

                        if last_message_sequence is not None:
                            missing = sequence - last_message_sequence - 1
                            if missing > 0:
                                print(f"Warning: {missing} message packets missing (last seq: {last_message_sequence}, current seq: {sequence})")

                        last_message_sequence = sequence

                        print(f"Timestamp: {timestamp} | Message Sequence: {sequence_number} | Flight ID: {flight_id} | State: {flight_state} | Message: {message} | Signal: {rssi} dBm")
                    else:
                        print(f"Timestamp: {timestamp} | Unknown packet type: {packet_type} | Signal: {rssi}dBm")

                except ValueError as e:
                    print("Packet parsing warning:", e)
                
        except Exception as err:
            print("Packet parsing warning:", err)
            
    time.sleep_ms(5) #tiny delay to allow other tasks to run