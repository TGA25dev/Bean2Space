
import time
from machine import Pin, I2C

from software.utils.mpu6050 import MPU6050
from software.utils.bmp280 import BMP280

from software.utils.buzzer_manager import BuzzerManager
buzzer = BuzzerManager(2) #pin 2

from software.utils.led_manager import LEDManager
onboard_led = LEDManager(1) #LED on pin 1

i2c = I2C(0, sda=Pin(5), scl=Pin(6))

bmp280 = BMP280(i2c, addr=0x76)
imu = MPU6050(i2c)

imu.set_accel_range(imu.AccelRange.RANGE_16_G) #set to 16G
imu.set_filter_bandwidth(imu.FilterBandwidth.BAND_21_HZ) #Filters out high frequency (motor vibrations I think)
imu.set_gyro_range(imu.GyroRange.RANGE_2000_DEG) # set to 2000 deg/s for better resolution during probable spins

ground_pressure  = 0.0 #base ground pressure value to be set during calibration

imu_offsets = { #default offset values for calibration
    "ay": 0.0,
    "ax": 0.0,
    "az": 0.0,
    "gx": 0.0,
    "gy": 0.0,
    "gz": 0.0
}

def calibrate_sensors() -> tuple:
    """
    Perfoms sensors calibrations

    args:
        None

    returns:
        imu_offsets (dict): A dictionary containing calibration offsets for accelerometer and gyroscope
    """

    print("Initializing Calibration...")
    
    for _ in range(10): #informs calibration process is starting
        buzzer.on()
        onboard_led.on()
        time.sleep(0.05) # Fast chirps
        onboard_led.off()
        buzzer.off()
        time.sleep(0.05)
    
    time.sleep(5) #pause to let the rocket in place and stable
    print("Sampling calibration data...")

    press_readings = []
    acc_y_readings = []
    acc_x_readings = []
    acc_z_readings = []
    gyro_x_readings = []
    gyro_y_readings = []
    gyro_z_readings = []
    
    #collects 50 samples for stable average
    for _ in range(50):
        press_readings.append(bmp280.pressure)

        ax, ay, az = imu.get_accel_data(as_g=True)
        acc_x_readings.append(ax)
        acc_y_readings.append(ay)
        acc_z_readings.append(az)

        gx, gy, gz = imu.get_gyro_data()
        gyro_x_readings.append(gx)
        gyro_y_readings.append(gy)
        gyro_z_readings.append(gz)

        time.sleep(0.02)

    ground_pressure = sum(press_readings) / len(press_readings)

    global imu_offsets

    imu_offsets = {
        "ax": sum(acc_x_readings) / 50,
        "ay": (sum(acc_y_readings) / 50) - 1.0, #subtracts 1g from the y axis to account for gravity
        "az": sum(acc_z_readings) / 50,
        "gx": sum(gyro_x_readings) / 50,
        "gy": sum(gyro_y_readings) / 50,
        "gz": sum(gyro_z_readings) / 50
    }

    print(f"Base Ground Pressure: {ground_pressure} Pa")
    print(f"Gyro Drifts (X,Y,Z): {imu_offsets['gx']:.2f}, {imu_offsets['gy']:.2f}, {imu_offsets['gz']:.2f} deg/s")

    onboard_led.on() #notifies end of calibration
    buzzer.on()
    time.sleep(1.0) 
    buzzer.off()
    onboard_led.off()

    return ground_pressure, imu_offsets
