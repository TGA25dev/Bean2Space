import time 

class RocketState:
    def __init__(self):
        self.state = "standby"
        self.filtered_altitude = 0.0
        self.last_altitude = 0.0
        self.last_time_ms = None
        self.velocity = 0.0
        self.max_altitude = 0.0

        self.launch_count = 0
        self.apogee_count = 0
        self.landed_count = 0

    def update(self, altitude, calibrated=True, now_ms=None):
        if now_ms is None:
            now_ms = time.ticks_ms()

        self._update_motion(altitude, now_ms)

        if self.state == "standby":
            if calibrated:
                self.state = "armed"
                return "ARMED"

        elif self.state == "armed":
            if self.filtered_altitude > 2.0:
                self.launch_count += 1
            else:
                self.launch_count = 0

            if self.launch_count >= 2: #if above 2 meters for 2 consecutive reads
                self.state = "flight"
                self.max_altitude = self.filtered_altitude
                return "LAUNCH_DETECTED"

        elif self.state == "flight":
            self.max_altitude = max(self.max_altitude, self.filtered_altitude)

            descending = self.velocity <= 0.2

            dropped_from_peak = (self.max_altitude - self.filtered_altitude) > 1.5 #if dropped more than 1.5m from peak alt it means its descending

            if descending and dropped_from_peak:
                self.apogee_count += 1

            else:
                self.apogee_count = 0

            if self.apogee_count >= 3: #if descending and dropped from peak for 3 consecutive reads apogee has been reached
                self.state = "descent"
                return "APOGEE_DETECTED"

        elif self.state == "descent":
            stable_near_ground = (self.filtered_altitude < 2.5 and abs(self.velocity) < 0.3) #if below 2.5m and velocity is low means it has landed

            if stable_near_ground:
                self.landed_count += 1

            else:

                self.landed_count = 0

            if self.landed_count >= 15: #landed for 15 reads

                self.state = "landed"
                return "TOUCHDOWN_DETECTED"

        return None

    def _update_motion(self, altitude, now_ms):
        if self.last_time_ms is None:
            self.filtered_altitude = altitude

        else:
            self.filtered_altitude = (self.filtered_altitude * 0.7+ altitude * 0.3) #filtered to reduce noise

            delta_ms = time.ticks_diff(now_ms, self.last_time_ms)

            if delta_ms > 0:
                raw_velocity = (self.filtered_altitude - self.last_altitude) / (delta_ms / 1000.0) #velocity in m/s

                self.velocity = (self.velocity * 0.8 + raw_velocity * 0.2) #filtered velocity

        self.last_altitude = self.filtered_altitude
        self.last_time_ms = now_ms