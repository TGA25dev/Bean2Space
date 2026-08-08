import espnow #type: ignore
import network
import wifi
import time

time.sleep(3)

print("\n" + "="*40)
print("SYSTEM BOOT: trigger station started!")
print("="*40 + "\n")

wifi.reset(sta=True, ap=False, channel=6) #start wifi in station mode (channel 6) and disable AP mode

wlan = network.WLAN(network.STA_IF)
wlan.config(protocol=network.MODE_LR) #type: ignore #enable LR Mode

receiver = espnow.ESPNow()
receiver.active(True)

#create a pre allocated storage list to grab the RSSI
telemetry_packet = [bytearray(6), bytearray(250), 0, 0] # [mac_address, message_buffer, rssi, timestamp]

print("Ground Stations is active! Waiting for telemetry packets...")

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
                    timestamp, packet_type, flight_id= data_payload.split(',')[:3]

                    if packet_type == "telemetry":
                        timestamp, packet_type, flight_id, temperature, absolute_pressure, relative_pressure, altitude, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp_imu = data_payload.split(',') #classic telemetry mode
                        print(f"Timestamp: {timestamp} | Flight ID: {flight_id} | Temperature: {temperature}°C | Absolute Pressure: {absolute_pressure}Pa | Relative Pressure: {relative_pressure}Pa | Altitude {altitude}m |Accel x: {accel_x} | Accel y: {accel_y}| Accel z: {accel_z} | Gyro x: {gyro_x} | Gyro y: {gyro_y} | Gyro z: {gyro_z} | IMU Temperature: {temp_imu}°C | Signal: {rssi}dBm")
                        
                    elif packet_type == "message":
                        timestamp, packet_type, flight_id, message = data_payload.split(',') #message mode
                        print(f"Timestamp: {timestamp} | Flight ID: {flight_id} | Message: {message} | Signal: {rssi}dBm")
                    
                    else:
                        print(f"Timestamp: {timestamp} | Unknown packet type: {packet_type} | Signal: {rssi}dBm")

                except ValueError as e:
                    print("Packet parsing warning:", e)
                
        except Exception as err:
            print("Packet parsing warning:", err)
            
    time.sleep_ms(5) #tiny delay to allow other tasks to run