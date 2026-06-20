import time

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

from software.utils.wifi_manager import start_access_point, check_for_connections, setup_web_server, handle_web_request
from software.modules.calibration import calibrate_sensors
from software.modules.telemetry import get_telemetry

def power_up() -> None:
    """
    Performs the power-up sequence

    args:
        None

    returns:
        None
    """

    print("Powering up the system...")

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

    calibrated = False
    while True:  #Main loop

        if not calibrated:
            time.sleep(1.5)
            imu_offsets = calibrate_sensors()
            calibrated = True
            print("Calibration complete! System Armed.")
        
        if calibrated: #only get telemetry after calibration is done to avoid wrong readings
            telemetry = get_telemetry(imu_offsets) #get telemetry from sensors (calibration offsets applied)

            #send telemetry somewhere and do stuff with it here
        
        handle_web_request(server_socket)  # Handle one request (non blocking for other taks)

        time.sleep(0.1)

power_up() #starts main sequence