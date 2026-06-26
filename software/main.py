import time
import random

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

from software.utils.wifi_manager import start_access_point, check_for_connections, setup_web_server, handle_web_request, stop_access_point
from software.modules.calibration import calibrate_sensors
from software.modules.telemetry import get_telemetry
from software.modules.esp_now import send_telemetry, send_message, start_wireless_transmiter

ground_station_mac = b'X\x8c\x81\xae\x16\xb0'
calibrated = False
esp_now_ready = False
esp_now_should_start = False
ap_should_stop = False
ground_pressure = 0.0

timestamp = 0.0
_last_tick = time.ticks_ms()

flight_id = random.randint(1000, 9999)

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

def power_up() -> None:
    """
    Performs the power-up sequence

    args:
        None

    returns:
        None
    """

    global ground_station_mac, calibrated ,esp_now_ready ,timestamp, flight_id
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
        
        for _ in range(3):
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
            ground_pressure, imu_offsets = calibrate_sensors()
            calibrated = True
            print("Calibration complete! System Armed.")
        
        if ap_should_stop or esp_now_should_start: #check if state change was requested by the web panel
            time.sleep(0.1)
            
            try:
                server_socket.close() #close webserver first
            except:
                pass
                
            stop_access_point(wifi_access_point)
            break  #stop server

        if calibrated:
            telemetry = get_telemetry(imu_offsets, ground_pressure)
            #print(telemetry)

        handle_web_request(server_socket) #handle webpanel requests

        update_system_clock()
        time.sleep(0.05)

    if esp_now_should_start:
        print("Starting ESPNOW transmitter...")
        transmitter = start_wireless_transmiter(ground_station_mac)
        esp_now_ready = True

        print("Entering Flight Mode... Telemetry will be sent to the ground station")

    else:
        print("System entered passive holding mode. Standing by...")


    while True:
        if esp_now_ready and calibrated:
            telemetry = get_telemetry(imu_offsets, ground_pressure)
            #print(f"[{timestamp}] Flight Telemetry: {telemetry}")

            send_telemetry(transmitter, ground_station_mac, telemetry, timestamp, flight_id)
            #send_message(transmitter, ground_station_mac, "Hello World!", timestamp, flight_id)

        update_system_clock()
        time.sleep(0.1) #10Hz sampling rate 

power_up() #starts main sequence