"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """

        try:
            sender = Command(cls.__private_key, connection, target, local_logger)
            local_logger.info("Successfully created a Command object")
            return True, sender
        # Catching all exceptions in fallible create() method
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            local_logger.error(f"Error in creating Command object: {e}")
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        # Do any intializiation here

        self.__connection = connection
        self.__target = target
        self.__local_logger = local_logger
        self.__total_velocity_x = 0
        self.__total_velocity_y = 0
        self.__total_velocity_z = 0
        self.__avg_velocity_x = 0
        self.__avg_velocity_y = 0
        self.__avg_velocity_z = 0
        self.__count = 0

    def run(self, data: telemetry.TelemetryData) -> "tuple[True, str] | tuple[False, None]":
        """
        Make a decision based on received telemetry data.
        """

        self.__count += 1

        # Log average velocity for this trip so far

        self.__total_velocity_x += data.x_velocity
        self.__total_velocity_y += data.y_velocity
        self.__total_velocity_z += data.z_velocity

        self.__avg_velocity_x = self.__total_velocity_x / self.__count
        self.__avg_velocity_y = self.__total_velocity_y / self.__count
        self.__avg_velocity_z = self.__total_velocity_z / self.__count

        self.__local_logger.info(f"Average velocity for X: {self.__avg_velocity_x:.3f} m/s")
        self.__local_logger.info(f"Average velocity for Y: {self.__avg_velocity_y:.3f} m/s")
        self.__local_logger.info(f"Average velocity for Z: {self.__avg_velocity_z:.3f} m/s")

        # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
        # The appropriate commands to use are instructed below

        # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
        # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"

        try:
            if abs(self.__target.z - data.z) > 0.5:
                self.__connection.mav.command_long_send(
                    1, 0, 113, 0, 1, 0, 0, 0, 0, 0, self.__target.z
                )
                self.__local_logger.info("Successfully sent CHANGE_ALTITUDE message")
                return True, f"CHANGE ALTITUDE: {self.__target.z - data.z}"

            # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
            # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
            # Positive angle is counter-clockwise as in a right handed system

            angle = math.atan2(self.__target.y - data.y, self.__target.x - data.x)
            target_angle_deg = angle * (180 / math.pi)

            data_angle_deg = data.yaw * (180 / math.pi)

            delta_angle = target_angle_deg - data_angle_deg
            delta_angle = (delta_angle + 180) % 360 - 180

            if abs(delta_angle) > 5:
                self.__connection.mav.command_long_send(
                    1,
                    0,
                    115,
                    0,
                    abs(delta_angle),
                    5,
                    0,
                    1,
                    0,
                    0,
                    0,
                )

                self.__local_logger.info("Successfully sent CHANGING YAW message")
                return True, f"CHANGING YAW: {delta_angle}"

            return False, None

        # Catching all exceptions in fallible run() method
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            self.__local_logger.error(f"Unable to send COMMAND_LONG messages, {e}")

        return False, None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
