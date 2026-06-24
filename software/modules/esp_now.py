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

    sender.add_peer(ground_station_mac) #add it as peer

    print("Wireless transmiter is ready !")

    return sender

def send_telemetry(sender:espnow.ESPNow, c3_ground_mac:bytes, telemetry_data:dict, packet_id:int):
    """
    Sends telemetry data to the ground station using ESPNow protocol

    args:
        sender (espnow.ESPNow): ESPNow sender object
        c3_ground_mac (bytes): MAC address of the ground station to send data to
        telemetry_data (dict): Dictionary containing telemetry data (altitude, velocity)
        packet_id (int): Packet ID for the telemetry data
    
    returns:
        tuple: (bool) ndicates if the packet was sent successfully
    
    """
    altitude = telemetry_data.get("altitude", 0.0) #NEEDS TO BE ADAPTED LATER TO THE REAL TELEMETRY DATA STRUCTURE
    velocity = telemetry_data.get("velocity", 0.0)
    telemetry_string = f"{packet_id},{altitude:.2f},{velocity:.1f}"
    
    try:
        sender.send(c3_ground_mac, telemetry_string, False) #False because no ACK (to avoid blocking the flight)
        return True

    except OSError:
        print("Error sending telemetry data")
        return False

c3_ground_mac = b'X\x8c\x81\xae\x16\xb0' #Ground Stations's MAC address


