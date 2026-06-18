"""
Heartbeat sending logic.
"""

from pymavlink import mavutil
from ..common.modules.logger import logger
from ..common.modules.logger.logger import Logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatSender:
    """
    HeartbeatSender class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger
    ) -> "tuple[True, HeartbeatSender] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatSender object.
        """

        try:
            sender = HeartbeatSender(cls.__private_key, connection, local_logger)
            local_logger.info("Successfully created a Heartbeat Sender object.")
            return True, sender
        except Exception as e:
            local_logger.error(f"Falied to create a Heartbeat Sender object, {e}")
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger
    ):
        assert key is HeartbeatSender.__private_key, "Use create() method"

        # Do any intializiation here

        self.__connection = connection
        self.__local_logger = local_logger


    def run(
        self
    ) -> bool:

        """
        Attempt to send a heartbeat message.
        """


        try:
            self.__connection.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                0
            )
            self.info("Successfully sent a Heartbeat message.")
            return True
        except Exception as e:
            self.error(f"Unable to send heartbeat message, {e}")
            return False


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
