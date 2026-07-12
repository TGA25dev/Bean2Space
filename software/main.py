import time
import random
import machine

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

from software.utils.wifi_manager import start_access_point, check_for_connections, setup_web_server, handle_web_request, stop_access_point
from software.modules.calibration import calibrate_sensors
from software.modules.telemetry import get_telemetry
from software.modules.esp_now import send_telemetry, send_message, start_wireless_transmiter

machine.freq(160000000)

ground_station_mac = b'X\x8c\x81\xae\x16\xb0'
calibrated = False
esp_now_ready = False
esp_now_should_start = False
ap_should_stop = False
telemetry = None

timestamp = 0.0
_last_tick = time.ticks_ms()

flight_id = random.randint(1000, 9999)
rocket_state = "standby" #possible states: standby, armed, flight, apogee, descent, landed 

ground_pressure = 0.0
max_altitude = 0.0
last_altitude = 0.0
last_time_ms = 0
velocity = 0.0
filtered_altitude = 0.0
launch_counter = 0

apogee_counter = 0
descent_counter = 0
landed_counter = 0

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

def check_rocket_state(altitude: float) -> None:
    """
    Updates the rocket state based on the current altitude, calculated velocity,
    and threshold filters to prevent false triggers from sensor noise

    args:
        altitude (float): Current altitude of the rocket in meters

    returns:
        None
    """

    global rocket_state, max_altitude, last_altitude, last_time_ms, velocity, filtered_altitude
    global launch_counter, apogee_counter, descent_counter, landed_counter

    current_time_ms = time.ticks_ms()

    if last_time_ms == 0: #first reading so no previous data to compare to
        filtered_altitude = altitude
    else:
        filtered_altitude = (filtered_altitude * 0.7) + (altitude * 0.3) #smooths out altitude readings to reduce noise
    
    if last_time_ms > 0:
        delta_t = time.ticks_diff(current_time_ms, last_time_ms) / 1000.0 #convert ms to seconds

        if delta_t > 0:
            raw_velocity = (filtered_altitude - last_altitude) / delta_t #raw velocity is calculated as the change in altitude over the change in time (m/s)
            
            velocity = (velocity * 0.8) + (raw_velocity * 0.2) #smooths out velocity readings to reduce noise (bcz again we don't like noise)
            
    last_altitude = filtered_altitude
    last_time_ms = current_time_ms

    if rocket_state == "standby" and calibrated:
        rocket_state = "armed"
        launch_counter = 0
        apogee_counter = 0
        descent_counter = 0
        landed_counter = 0

        print("Rocket is now ARMED! Ready for launch")

    elif rocket_state == "armed":
        if filtered_altitude > 2.0: #alt exceeds 2 meters
            launch_counter += 1

            if launch_counter >= 3: #2m up for 3 consecutives readings
                rocket_state = "flight"
                max_altitude = filtered_altitude
                apogee_counter = 0
                descent_counter = 0
                landed_counter = 0
                print("LAUNCH DETECTED! Rocket is in FLIGHT mode!")
        else:
            launch_counter = 0

    elif rocket_state == "flight":
        if filtered_altitude > max_altitude: #keep track of max altitude reached during the flight
            max_altitude = filtered_altitude

        if velocity <= 0.2 and (max_altitude - filtered_altitude) > 1.5: #if descending and dropped more than 1.5m from peak
            apogee_counter += 1
            if apogee_counter >= 3: #3 readings to confirm
                rocket_state = "apogee"
                descent_counter = 0
                landed_counter = 0
                print(f"APOGEE DETECTED! Peak Altitude: {max_altitude:.2f}m")
        else:
            apogee_counter = 0 #reset counter

    elif rocket_state == "apogee":
        rocket_state = "descent"
        descent_counter = 0
        print("Transitioning to DESCENT mode")

    elif rocket_state == "descent":
        if velocity < -1.0: #negative velocity (descending) and faster than 1 m/s
            descent_counter += 1
            if descent_counter >= 3: #3 readings again
                descent_counter = 0 
                
        if filtered_altitude < 3.0 and abs(velocity) < 0.3: #alt below 3 meters and velocity close to 0
            landed_counter += 1

            if landed_counter >= 20: #stable for 20 readings (~2 seconds at 10Hz)
                rocket_state = "landed"
                print("TOUCHDOWN has been detected!")
        else:
            landed_counter = 0

    elif rocket_state == "landed":
        #TODO: implement post landing procedeures
        pass

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
            check_rocket_state(telemetry["altitude"])
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
            
            telemetry = get_telemetry(imu_offsets, ground_pressure, demo=False)
            check_rocket_state(telemetry["altitude"])

            #DEBUG
            #print(rocket_state, telemetry["altitude"])
            #print(f"[{timestamp}] Flight Telemetry: {telemetry}")
            #END DEBUG

            send_telemetry(transmitter, ground_station_mac, telemetry, timestamp, flight_id)
            #send_message(transmitter, ground_station_mac, "Hello World!", timestamp, flight_id)

        update_system_clock()
        time.sleep(0.1) #10Hz sampling rate 

power_up() #starts main sequence