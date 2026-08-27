import espnow # type: ignore
import network
import software.utils.wifi as wifi

def start_wireless_transmiter(ground_station_mac:bytes):
    """
    Starts wireless transmiter (espnow) and returns the sender object to be used later

    args:
        ground_station_mac (bytes): MAC address of the ground station to send data to
    
    returns:
        sender (espnow.ESPNow): ESPNow sender object
    """

    wifi.reset(sta=True, ap=False, channel=6) #clean wifi boot

    wlan = network.WLAN(network.STA_IF)
    wlan.config(protocol=network.MODE_LR)  # type: ignore #enables Long Range mode

    sender = espnow.ESPNow()
    sender.active(True)

    try:
        sender.add_peer(ground_station_mac) #add it as peer
        print("Peer added successfully.")

    except OSError as e:
        if e.args[0] == -12395 or "ESP_ERR_ESPNOW_EXIST" in str(e):
            print("Peer already exists, skipping...")
        else:
            raise e # Raise other OSErrors

    print("Wireless transmiter is ready !")

    return sender

def send_telemetry(sender:espnow.ESPNow, ground_station_mac:bytes, telemetry_data:dict, timestamp:float, flight_id:int, telemetry_sequence_number:int, flight_state:str) -> bool:
    """
    Sends telemetry data to the ground station using ESPNow protocol

    args:
        sender (espnow.ESPNow): ESPNow sender object
        ground_station_mac (bytes): MAC address of the ground station to send data to
        telemetry_data (dict): Dictionary containing telemetry data (altitude, velocity)
        timestamp (float): Current timestamp to be sent with the telemetry data
        flight_id (int): Unique flight identifier to be sent with the telemetry data
        telemetry_sequence_number (int): Sequence number of the telemetry packet to be sent
        flight_state (str): Current state of the flight to be sent with the telemetry data
    
    returns:
        tuple: (bool) ndicates if the packet was sent successfully
    
    """
    
    temperature = telemetry_data.get("temperature", 0.0)
    absolute_pressure = telemetry_data.get("absolute_pressure", 0.0)
    relative_pressure = telemetry_data.get("relative_pressure", 0.0)
    altitude = telemetry_data.get("altitude", 0.0)
    accel_x = telemetry_data.get("accel_x", 0.0)
    accel_y = telemetry_data.get("accel_y", 0.0)
    accel_z = telemetry_data.get("accel_z", 0.0)
    gyro_x = telemetry_data.get("gyro_x", 0.0)
    gyro_y = telemetry_data.get("gyro_y", 0.0)
    gyro_z = telemetry_data.get("gyro_z", 0.0)
    temp_imu = telemetry_data.get("temp_imu", 0.0)

    packet_type = "telemetry"
    
    telemetry_string = f"{timestamp},{packet_type},{telemetry_sequence_number},{flight_state},{flight_id},{temperature:.2f},{absolute_pressure:.2f},{relative_pressure:.2f},{altitude:.2f},{accel_x:.4f},{accel_y:.4f},{accel_z:.4f},{gyro_x:.4f},{gyro_y:.4f},{gyro_z:.4f},{temp_imu:.2f}"
    
    try:
        result = sender.send(ground_station_mac, telemetry_string, True) #True/False ACK flag
        return bool(result)

    except OSError as e:
        print("Error sending telemetry data: ", e)
        return False


def send_message(sender:espnow.ESPNow, ground_station_mac:bytes, message:str, timestamp:float, flight_id:int, message_sequence_number:int, flight_state:str) -> bool:
    """
    Sends a message to the ground station using ESPNow protocol
    
    args:
        sender (espnow.ESPNow): ESPNow sender object
        ground_station_mac (bytes): MAC address of the ground station to send data to
        message (str): Message string to be sent
        timestamp (float): Current timestamp to be sent with the message
        flight_id (int): Unique flight identifier to be sent with the message
        message_sequence_number (int): Sequence number of the message packet to be sent
        flight_state (str): Current state of the flight to be sent with the message
        
    returns:
        bool: Indicates if the message was sent successfully
    """

    packet_type = "message"
    message_string = f"{timestamp},{packet_type},{message_sequence_number},{flight_state},{flight_id},{message}"

    try: 
        sender.send(ground_station_mac, message_string, False) #False because no ACK (to avoid blocking the flight)
        return True
    
    except OSError as e:
        print("Error sending message:", e)
        return False

c3_ground_mac = b'X\x8c\x81\xae\x16\xb0' #Ground Stations's MAC address


