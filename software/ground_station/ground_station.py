import espnow #type: ignore
import network
import wifi
import time

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
                pkt_id, alt, vel = data_payload.split(',')
                
                print(f"Pkt: {pkt_id} | Alt: {alt}m | Vel: {vel}m/s | Signal: {rssi}dBm")
                
        except Exception as err:
            print("Packet parsing warning:", err)
            
    time.sleep_ms(5) #tiny delay to allow other tasks to run