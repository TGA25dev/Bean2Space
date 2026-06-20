"""!
@file mpu6050.py
@brief Micropython module for the MPU6050 6-DoF sensor.
@details This module provides a class to interface with the MPU6050 accelerometer
         and gyroscope sensor over I2C.
@author Adafruit (Original C++ library)
@author Gemini (Micropython conversion)
@date August 2, 2025
@version 1.1
"""

import struct
from machine import I2C
from time import sleep_ms

## @name Register Map
#  @{
_MPU6050_DEFAULT_ADDR = 0x68  ##< Default I2C address
_MPU6050_DEVICE_ID = 0x68      ##< Device ID stored in WHO_AM_I register
_MPU6050_SMPLRT_DIV = 0x19     ##< Sample Rate Divider register
_MPU6050_CONFIG = 0x1A         ##< Configuration register
_MPU6050_GYRO_CONFIG = 0x1B    ##< Gyroscope Configuration register
_MPU6050_ACCEL_CONFIG = 0x1C   ##< Accelerometer Configuration register
_MPU6050_ACCEL_OUT = 0x3B      ##< Base address for accelerometer data registers
_MPU6050_TEMP_OUT = 0x41       ##< Base address for temperature data registers
_MPU6050_GYRO_OUT = 0x43       ##< Base address for gyroscope data registers
_MPU6050_PWR_MGMT_1 = 0x6B     ##< Power Management 1 register
_MPU6050_WHO_AM_I = 0x75       ##< WHO_AM_I register, contains device ID
## @}

SENSORS_GRAVITY_STANDARD = 9.80665 ##< Standard gravity for conversion to m/s^2

class MPU6050:
    """!
    @brief Driver class for the MPU6050 sensor.
    @details Allows reading of acceleration, gyroscope, and temperature data.
    """

    ## @name Configuration Constants
    #  @{

    ## @brief Accelerometer measurement range
    class AccelRange:
        RANGE_2_G = 0x00  ##< +/- 2g
        RANGE_4_G = 0x01  ##< +/- 4g
        RANGE_8_G = 0x02  ##< +/- 8g
        RANGE_16_G = 0x03 ##< +/- 16g

    ## @brief Gyroscope measurement range
    class GyroRange:
        RANGE_250_DEG = 0x00  ##< +/- 250 deg/s
        RANGE_500_DEG = 0x01  ##< +/- 500 deg/s
        RANGE_1000_DEG = 0x02 ##< +/- 1000 deg/s
        RANGE_2000_DEG = 0x03 ##< +/- 2000 deg/s

    ## @brief Digital Low Pass Filter bandwidth
    class FilterBandwidth:
        BAND_260_HZ = 0x00 ##< 260 Hz
        BAND_184_HZ = 0x01 ##< 184 Hz
        BAND_94_HZ = 0x02  ##< 94 Hz
        BAND_44_HZ = 0x03  ##< 44 Hz
        BAND_21_HZ = 0x04  ##< 21 Hz
        BAND_10_HZ = 0x05  ##< 10 Hz
        BAND_5_HZ = 0x06   ##< 5 Hz
    ## @}

    # Sensitivity scales based on datasheet
    _ACCEL_SCALES = {
        AccelRange.RANGE_2_G: 16384.0,
        AccelRange.RANGE_4_G: 8192.0,
        AccelRange.RANGE_8_G: 4096.0,
        AccelRange.RANGE_16_G: 2048.0,
    }

    _GYRO_SCALES = {
        GyroRange.RANGE_250_DEG: 131.0,
        GyroRange.RANGE_500_DEG: 65.5,
        GyroRange.RANGE_1000_DEG: 32.8,
        GyroRange.RANGE_2000_DEG: 16.4,
    }

    def __init__(self, i2c: I2C, address: int = _MPU6050_DEFAULT_ADDR):
        """!
        @brief Initializes the MPU6050 sensor.
        @param i2c The Micropython I2C object.
        @param address The I2C address of the sensor (default is 0x68).
        """
        self.i2c = i2c
        self.address = address
        self._accel_range = self.AccelRange.RANGE_2_G
        self._gyro_range = self.GyroRange.RANGE_250_DEG

        if self._read_u8(_MPU6050_WHO_AM_I) != _MPU6050_DEVICE_ID:
            raise RuntimeError(f"MPU6050 not found at I2C address {hex(self.address)}")

        self.reset()
        self.set_accel_range(self.AccelRange.RANGE_2_G)
        self.set_gyro_range(self.GyroRange.RANGE_500_DEG)
        self.set_filter_bandwidth(self.FilterBandwidth.BAND_260_HZ)
        self._write_u8(_MPU6050_PWR_MGMT_1, 0x01)  # Wake up sensor, set clock to Gyro X PLL
        sleep_ms(100)

    def _read_u8(self, register: int) -> int:
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def _write_u8(self, register: int, value: int):
        self.i2c.writeto_mem(self.address, register, bytearray([value]))

    def _read_bytes(self, register: int, length: int) -> bytes:
        return self.i2c.readfrom_mem(self.address, register, length)

    def reset(self):
        """!
        @brief Resets sensor registers to their default values.
        """
        self._write_u8(_MPU6050_PWR_MGMT_1, 0x80)
        sleep_ms(100)

    def set_accel_range(self, accel_range: int):
        """!
        @brief Sets the accelerometer measurement range.
        @param accel_range Use constants from MPU6050.AccelRange.
        """
        if accel_range not in self._ACCEL_SCALES:
            raise ValueError("Invalid accelerometer range")
        self._write_u8(_MPU6050_ACCEL_CONFIG, accel_range << 3)
        self._accel_range = accel_range

    def set_gyro_range(self, gyro_range: int):
        """!
        @brief Sets the gyroscope measurement range.
        @param gyro_range Use constants from MPU6050.GyroRange.
        """
        if gyro_range not in self._GYRO_SCALES:
            raise ValueError("Invalid gyroscope range")
        self._write_u8(_MPU6050_GYRO_CONFIG, gyro_range << 3)
        self._gyro_range = gyro_range

    def set_filter_bandwidth(self, bandwidth: int):
        """!
        @brief Sets the Digital Low-Pass Filter bandwidth.
        @param bandwidth Use constants from MPU6050.FilterBandwidth.
        """
        if not 0x00 <= bandwidth <= 0x06:
            raise ValueError("Invalid filter bandwidth")
        self._write_u8(_MPU6050_CONFIG, bandwidth)

    def get_accel_data(self, as_g: bool = False) -> tuple[float, float, float]:
        """!
        @brief Reads and converts the accelerometer data.
        @param as_g If True, returns values in 'g'. Otherwise, returns in m/s^2 (default).
        @return A tuple of 3 floats (x, y, z).
        """
        data = self._read_bytes(_MPU6050_ACCEL_OUT, 6)
        raw_x, raw_y, raw_z = struct.unpack('>hhh', data)
        
        scale = self._ACCEL_SCALES[self._accel_range]
        x = raw_x / scale
        y = raw_y / scale
        z = raw_z / scale
        
        if as_g:
            return x, y, z
        
        return x * SENSORS_GRAVITY_STANDARD, y * SENSORS_GRAVITY_STANDARD, z * SENSORS_GRAVITY_STANDARD

    def get_gyro_data(self) -> tuple[float, float, float]:
        """!
        @brief Reads and converts the gyroscope data in degrees per second.
        @return A tuple of 3 floats (x, y, z) in °/s.
        """
        data = self._read_bytes(_MPU6050_GYRO_OUT, 6)
        raw_x, raw_y, raw_z = struct.unpack('>hhh', data)
        
        scale = self._GYRO_SCALES[self._gyro_range]
        x = raw_x / scale
        y = raw_y / scale
        z = raw_z / scale
        
        return x, y, z

    def get_temp_data(self) -> float:
        """!
        @brief Reads and converts the temperature data.
        @return The temperature in degrees Celsius.
        """
        data = self._read_bytes(_MPU6050_TEMP_OUT, 2)
        raw_temp = struct.unpack('>h', data)[0]
        temp_c = (raw_temp / 340.0) + 36.53
        return temp_c

    def get_all_data(self) -> dict:
        """!
        @brief Reads all sensor data in a single, efficient transaction.
        @return A dictionary containing 'accel' (m/s^2), 'gyro' (°/s), and 'temp' (°C).
        """
        data = self._read_bytes(_MPU6050_ACCEL_OUT, 14)
        raw_ax, raw_ay, raw_az, raw_t, raw_gx, raw_gy, raw_gz = struct.unpack('>hhhhhhh', data)
        
        accel_scale = self._ACCEL_SCALES[self._accel_range]
        ax = (raw_ax / accel_scale) * SENSORS_GRAVITY_STANDARD
        ay = (raw_ay / accel_scale) * SENSORS_GRAVITY_STANDARD
        az = (raw_az / accel_scale) * SENSORS_GRAVITY_STANDARD
        
        temp = (raw_t / 340.0) + 36.53
        
        gyro_scale = self._GYRO_SCALES[self._gyro_range]
        gx = raw_gx / gyro_scale
        gy = raw_gy / gyro_scale
        gz = raw_gz / gyro_scale
        
        return {'accel': (ax, ay, az), 'gyro': (gx, gy, gz), 'temp': temp}