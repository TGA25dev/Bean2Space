import time
import random
import machine

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(4) #pin 4

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

from software.utils.wifi_manager import start_access_point, check_for_connections, setup_web_server, handle_web_request, stop_access_point
from software.modules.calibration import calibrate_sensors
from software.modules.telemetry import get_telemetry
from software.modules.esp_now import send_telemetry, send_message, start_wireless_transmiter

from software.utils.internal_temp_manager import read_internal_temp, check_internal_temp

from software.modules.state_manager import RocketState

machine.freq(160000000)

ground_station_mac = b'X\x8c\x81\xae\x16\xb0'
calibrated = False
esp_now_ready = False
esp_now_should_start = False
ap_should_stop = False
telemetry = None
transmitter = None

telemetry_sequence_number = 0
message_sequence_number = 0

timestamp = 0.0
_last_tick = time.ticks_ms()

flight_id = random.randint(1000, 9999)
rocket = RocketState()

ground_pressure = 0.0
imu_offsets = {
    "ay": 0.0,
    "ax": 0.0,
    "az": 0.0,
    "gx": 0.0,
    "gy": 0.0,
    "gz": 0.0
}

def send_live_log(text, level="INFO"):
    """
    Sends a live log message to the ground station using the ESPNow protocol
    
    args:
        sender (espnow.ESPNow): ESPNow sender object
        text (str): the log message to be sent
        level (str): the log level (INFO, WARNING, ERROR)

    returns:
        bool: Indicates if the log message was sent successfully or not
    """

    global timestamp, flight_id, ground_station_mac, esp_now_ready, transmitter, message_sequence_number

    #print(esp_now_ready, transmitter)

    if not esp_now_ready or transmitter is None:
        print("ESPNow is not ready! Cannot send log message")
        return False

    message = f"[{level}]:{text}"
    message_sequence_number += 1
    sent_msg = send_message(transmitter, ground_station_mac, message, timestamp, flight_id, message_sequence_number, rocket.state)

    return sent_msg

def update_system_clock() -> None:
    """
    Updates the global timestamp variable based on the elapsed time since the last update

    args:
        None

    returns:
        None
    """
    global timestamp, _last_tick
    
    current_tick = time.ticks_ms()
    
    ms_passed = time.ticks_diff(current_tick, _last_tick)   #how many milliseconds passed since the last loop iteration
    
    timestamp += ms_passed / 1000.0 #converted to seconds

    _last_tick = current_tick

def handle_state_event(event:str):
    if event == "ARMED":
        send_live_log("Rocket is armed and ready for launch!", "INFO")

    elif event == "LAUNCH_DETECTED":
        send_live_log("Launch detected! Rocket is in flight!", "INFO")

    elif event == "APOGEE_DETECTED":
        send_live_log(f"Apogee detected! Apogee at {rocket.max_altitude}m !", "INFO")
        buzzer.on()
        time.sleep(0.2)
        buzzer.off()

    elif event == "TOUCHDOWN_DETECTED":
        send_live_log("Touchdown detected!", "INFO")

def apply_calibration() -> None:
    """
    Performs the calibration process and updates the global variables for ground pressure and IMU offsets

    args:
        None
    returns:
        None
    """

    global ground_pressure, imu_offsets, calibrated
    ground_pressure, imu_offsets = calibrate_sensors()
    calibrated = True

    time.sleep(0.5)
    print("Calibration complete! System Armed.")
    for _ in range(2):
        buzzer.on()
        onboard_led.on()
        time.sleep(0.15)
        buzzer.off()
        onboard_led.off()
        time.sleep(0.25)


def power_up() -> None:
    """
    Performs the power-up sequence

    args:
        None

    returns:
        None
    """

    global ground_pressure, calibrated, imu_offsets
    global esp_now_should_start, ap_should_stop
    global ground_station_mac, esp_now_ready ,timestamp, flight_id, transmitter, telemetry_sequence_number
    print(f"Powering up the system... (ID: {flight_id})")

    onboard_led.on()
    buzzer.on()
    time.sleep(0.2)
    
    buzzer.off()
    time.sleep(0.3)
    onboard_led.off()
    time.sleep(0.3)
    
    for _ in range(2):
        onboard_led.on()
        time.sleep(0.3)
        onboard_led.off()
        time.sleep(0.3)

    onboard_led.off()
    print("Greeting sequence completed !")

    print("Starting Wi-Fi Access Point...")
    wifi_access_point = start_access_point() 
    print(f"Access Point started successfully!")

    wait_for_connections_printed = True #print flag
    while not check_for_connections(wifi_access_point): #while no device is connected
        
        for _ in range(2):
            onboard_led.on()
            time.sleep(0.2)
            onboard_led.off()
            time.sleep(0.2)

        if wait_for_connections_printed:
            print("Waiting for devices to connect...")
            wait_for_connections_printed = False
        
        time.sleep(1)
    
    print("Device connected to the Access Point!")
    onboard_led.off()
    print("Starting web server...")

    server_socket = setup_web_server()  #initialize once the webserver socket
    print("Web server ready!")
    onboard_led.on()
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()
    onboard_led.off()

    print("System is fully operational! Starting main loop...")

    while True:
        if not calibrated: #calibrate if not done yet
            time.sleep(1.5)

            apply_calibration()

        if calibrated:
            telemetry = get_telemetry(imu_offsets, ground_pressure)
            #print(telemetry)

        web_command = handle_web_request(server_socket)
        if web_command == "start-esp-now":
            esp_now_should_start = True
            ap_should_stop = True

        elif web_command == "stop-ap":
            ap_should_stop = True
            
        elif web_command == "calibrate":
            apply_calibration()

        if ap_should_stop or esp_now_should_start: #check if state change was requested by the web panel
            print("Web command received: stopping Wi-Fi access point")
            time.sleep(0.1)
            
            try:
                server_socket.close() #close webserver first
            except:
                pass
                
            stop_access_point(wifi_access_point)
            break  #stop server

        update_system_clock()
        time.sleep(0.05)

        time.sleep(0.5)

    if esp_now_should_start:
        print("Starting ESPNOW transmitter...")
        try:
            transmitter = start_wireless_transmiter(ground_station_mac)
            print("ESPNOW transmitter initialized")
            esp_now_ready = True

        except Exception as error:
            print("ESPNOW startup failed:", repr(error))
            buzzer.on()
            time.sleep(1)
            buzzer.off()
            raise

        print("Entering Flight Mode... Telemetry will be sent to the ground station")
        print("Starting internal temperature monitoring...")

        for _ in range(3):
            onboard_led.on()
            buzzer.on()
            time.sleep(0.25)
            onboard_led.off()
            buzzer.off()
            time.sleep(0.25)
    else:
        print("System entered passive holding mode. Standing by...")

    wdt = machine.WDT(timeout=5000) #5s watchdog timer

    while True:
        if esp_now_ready and calibrated:
            
            telemetry = get_telemetry(imu_offsets, ground_pressure, demo=False)

            acceleration = (
                telemetry["accel_x"],
                telemetry["accel_y"],
                telemetry["accel_z"]
            )
            event = rocket.update(telemetry["altitude"], calibrated, acceleration=acceleration)
            
            if event:
                handle_state_event(event)

            telemetry_sequence_number += 1
            sent = send_telemetry(transmitter, ground_station_mac, telemetry, timestamp, flight_id, telemetry_sequence_number, rocket.state)
            if not sent:
                print("Radio transmission failed!")
        
        internal_temp_thresold_exceeded, current_temp = check_internal_temp(85.0) #thresold of 85C

        #DEBUG
        #print(f"Internal temperature: {current_temp:.2f}C")
        #print(event, telemetry["altitude"], acceleration, rocket.state)
        #print(f"[{timestamp}] Flight Telemetry: {telemetry}")
        #END DEBUG

        if not internal_temp_thresold_exceeded and current_temp >= 75.0:
            print(f"WARNING: Internal temperature is getting high ({current_temp:.2f}C)!")
            send_live_log(f"Internal temperature is getting high ({current_temp:.2f}C)!", "WARNING")

        elif internal_temp_thresold_exceeded:
            print("WARNING: Internal temperature exceeds threshold! ({current_temp:.2f}C) System may be overheating!")
            send_live_log("Internal temperature exceeds threshold! ({current_temp:.2f}C) System may be overheating!", "WARNING")

        wdt.feed() #reset watchdog timer
        update_system_clock()
        time.sleep(0.1) #10Hz sampling rate 

power_up() #starts main sequence