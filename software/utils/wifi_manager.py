import network
import socket
import time
import sys
if "/software" not in sys.path:
    sys.path.append("/software")

from modules.esp_now import start_wireless_transmiter

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

import __main__ #type: ignore

SSID = "HRC-01"
PASSWORD = "xiao1234"
PORT = 80

def start_access_point() -> network.WLAN:
    """
    Start a Wi-Fi Access Point with the specified SSID and PASSWORD

    args:
        None

    returns:
        network.WLAN: The access point object (ap)
    """

    ap = network.WLAN(network.AP_IF) #create access point interface (ap = access point)
    ap.active(False)
    time.sleep(1)
    ap.active(True)

    #force secured AP mode
    authmode = getattr(network, "AUTH_WPA_WPA2_PSK", None)
    ap.config(essid=SSID, password=PASSWORD, authmode=authmode) #Sets Auth

    while not ap.active():
        time.sleep(0.1)

    print("SSID:", SSID)
    print("Password:", PASSWORD)
    print("IP:", ap.ifconfig()[0])

    return ap

def stop_access_point(ap:network.WLAN) -> None:
    """
    Stops the Wifi access point
    
    args:
        ap (network.WLAN): The access point object

    returns:
        None
    """

    ap.active(False)
    print("Access point stopped!")

def check_for_connections(ap:network.WLAN) -> bool:
    """
    Check for connected devices to the access point.
    Return True if at least one device is connected, otherwise False

    args:
        ap (network.WLAN): The access point object
    
    returns:
        bool: True if at least one device is connected, otherwise False
    """

    connected_devices = ap.status('stations')
    return True if connected_devices else False


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>HRC-01 Dashboard</title>
</head>
<body>
    <h1>HRC-01 Control Panel</h1>
    <button onclick="showAlert()">Click Me</button>
    <button onclick="startCalibration()">Calibrate</button>
    <button onclick="stopAP()">Stop AP</button>
    <button onclick="startESPNow()">Start ESP Now</button>
    <button onclick="buzzer()">Buzzer</button>
    
    <script>
        function showAlert() {
            alert("You cliked me!");
        }

        function startCalibration() {
            alert("Calibration started!");
            fetch('/calibrate')
                .then(response => console.log("Calibration request sent"));
        }

        function buzzer() {
        fetch('/buzzer')
            .then(response => console.log("Buzzer request sent"));    
        }

        function stopAP() {
        alert("AP stopped (you will be disconnected from the Wi-Fi)");
        fetch('/stop-ap')
            .then(response => console.log("Stop AP request sent"));    
        }

        function startESPNow() {
        alert("ESP Now started (you will be disconnected from the Wi-Fi and the device will start sending telemetry to the ground station)");
        fetch('/start-esp-now')
            .then(response => console.log("Start ESP Now request sent"));    
        }

    </script>
</body>
</html>
""" #to be updated with telemetry and other things later

def setup_web_server(port=PORT) -> socket.socket:
    """
    Set up a simple web server that serves the HTML page

    args:
        port (int): The port number to listen on (default is 80)

    returns:
        socket.socket: The server socket object
    """
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('0.0.0.0', port))

    except OSError as e:
        if e.errno == 112: #EADDRINUSE
            print("Port 80 busy Resetting network interface to clear sockets...")
            
            server_socket.close() #close socket 
            
            #force cycle the interface to tear down zombie connections
            ap = network.WLAN(network.AP_IF)
            ap.active(False)
            time.sleep_ms(500)
            ap.active(True)
            while not ap.active():
                time.sleep_ms(50)
                
            # recreate socket and attempt binding again
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', port))
        else:
            raise e
            
    server_socket.listen(1)
    server_socket.setblocking(False)

    return server_socket
    
def handle_web_request(server_socket:socket.socket) -> None:
    """
    Handle one request if a client is waiting, then return

    args:
        server_socket (socket.socket): The server socket

    returns:
        None
    """

    try:
        client, addr = server_socket.accept()
        request = client.recv(1024).decode('utf-8')

        # Check what the browser is requesting
        if "GET /calibrate" in request:
            __main__.apply_calibration()

        if "GET /stop-ap" in request:
            __main__.ap_should_stop = True

        if "GET /buzzer" in request:
            buzzer.on()
            time.sleep(0.5)
            buzzer.off()

        if "GET /start-esp-now" in request:
            __main__.ap_should_stop = True
            __main__.esp_now_should_start = True

        
        response = "HTTP/1.1 200 OK\r\n"
        response += "Content-Type: text/html\r\n\r\n"
        response += HTML
        
        client.send(response.encode('utf-8'))
        client.close()
        
    except OSError:
        pass  #no client waiting we just don't do anything