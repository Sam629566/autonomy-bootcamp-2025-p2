"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple[True, Telemetry] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """
        try:
            receiver = Telemetry(cls.__private_key, connection, local_logger)
            local_logger.info("Successfully created Telemetry object")
            return True, receiver
        # Catching all exceptions in fallible create() method
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            local_logger.error(f"Unable to create Telemetry object, {e}")
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        # Do any intializiation here

        self.__connection = connection
        self.__local_logger = local_logger

    def run(
        self,
    ) -> "tuple[True, TelemetryData] | tuple[False, None]":
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        # Read MAVLink message LOCAL_POSITION_NED (32)
        # Read MAVLink message ATTITUDE (30)

        try:
            start_time = time.time()
            local_position = None
            attitude = None

            data = TelemetryData()

            while time.time() - start_time <= 1:
                msg1 = self.__connection.recv_match(
                    type="LOCAL_POSITION_NED", blocking=True, timeout=0.1
                )
                msg2 = self.__connection.recv_match(type="ATTITUDE", blocking=True, timeout=0.1)

                if msg1 is not None:
                    local_position = msg1
                if msg2 is not None:
                    attitude = msg2
                if local_position and attitude:
                    break

            # Return the most recent of both, and use the most recent message's timestamp
            if local_position and attitude:
                data.time_since_boot = max(local_position.time_boot_ms, attitude.time_boot_ms)
                data.x = local_position.x
                data.y = local_position.y
                data.z = local_position.z
                data.x_velocity = local_position.vx
                data.y_velocity = local_position.vy
                data.z_velocity = local_position.vz
                data.roll = attitude.roll
                data.pitch = attitude.pitch
                data.yaw = attitude.yaw
                data.roll_speed = attitude.rollspeed
                data.pitch_speed = attitude.pitchspeed
                data.yaw_speed = attitude.yawspeed

                self.__local_logger.info("Successfully created Telemetry Data object")
                return True, data

            self.__local_logger.warning(
                "Local Position and Attitude were not read, unable to create Telemetry Data object"
            )
            return False, None

        # Catching all exceptions in fallible run() method
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            self.__local_logger.error(f"Error while creating Telemetry Data object, {e}")
            return False, None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
