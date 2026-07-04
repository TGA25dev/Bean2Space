import time
from machine import Pin, I2C

from software.utils.mpu6050 import MPU6050
from software.utils.bmp280 import BMP280

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

from software.modules.calibration import ground_pressure

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

bmp280 = BMP280(i2c, addr=0x76)
imu = MPU6050(i2c)

imu.set_accel_range(imu.AccelRange.RANGE_16_G) #set to 16G
imu.set_filter_bandwidth(imu.FilterBandwidth.BAND_21_HZ) #Filters out high frequency (motor vibrations)
imu.set_gyro_range(imu.GyroRange.RANGE_2000_DEG) # set to 2000 deg/s for better resolution during probable spins

demo_alt = 0.0
demo_alt_counter = 0

def get_telemetry(imu_offsets:dict, ground_pressure:float, demo:bool=False) -> dict:
    """
    Reads all sensors and applies calibration offsets

    args:
        imu_offsets (dict): A dictionary containing calibration offsets for accelerometer and gyroscope
        ground_pressure (float): The ground pressure value obtained during calibration (fixed reference value)
        demo (bool): If True simulates altitude data for testing purposes

    returns:
        telemetry (dict): A dictionary containing the current telemetry data from the sensors
    """

    temp = bmp280.temperature

    absolute_pressure = bmp280.pressure #raw pressure from the sensor in Pa
    relative_pressure = absolute_pressure - ground_pressure #calculates pressure relative to launch pad ground level

    if ground_pressure > 0:
        altitude = 44330.0 * (1.0 - (absolute_pressure / ground_pressure) ** 0.1903) #calculates altitude based on the barometric formula, using the ground pressure as a reference
    else:
        altitude = 0.0

    if demo:
        global demo_alt, demo_alt_counter
        demo_alt_counter += 1
        if demo_alt_counter % 10 == 0: #increments demo alt every 10 calls
            demo_alt += 1.0
        altitude = demo_alt

    imu_raw = imu.get_all_data()

    ax = (imu_raw['accel'][0] / 9.80665) - imu_offsets['ax'] #gravity is 9.80665 m/s ^2 , so we convert to g's for better readability
    ay = (imu_raw['accel'][1] / 9.80665) - imu_offsets['ay']
    az = (imu_raw['accel'][2] / 9.80665) - imu_offsets['az']
    
    gx = imu_raw['gyro'][0] - imu_offsets['gx'] #substracts the offsets found during calibration
    gy = imu_raw['gyro'][1] - imu_offsets['gy']
    gz = imu_raw['gyro'][2] - imu_offsets['gz']

    telemetry = {
        "temperature": temp,
        "absolute_pressure": absolute_pressure,
        "relative_pressure": relative_pressure,
        "altitude": altitude,
        "accel_x": ax,
        "accel_y": ay,
        "accel_z": az,
        "gyro_x": gx,
        "gyro_y": gy,
        "gyro_z": gz,
        "temp_imu": imu_raw['temp']
    }

    return telemetry
