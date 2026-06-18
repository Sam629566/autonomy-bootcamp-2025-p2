"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple[True, HeartbeatReceiver] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """


        try:
            reciever = HeartbeatReceiver(cls.__private_key, connection, local_logger)
            local_logger.info("Successfully created a HeartbeatReciever object")
            return True, reciever
        except Exception as e:
            local_logger.error(f"Unable to create a HeartbeatReciever object: {e}")
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        self.__connection = connection
        self.__local_logger = local_logger
        self.__count = 0
        self.__status = "Disconnected"

        # Do any intializiation here

    def getStatus(self) -> str:
        """
        Returns the current connection status: Connected/Disconnected
        """
        return self.__status

    def run(
        self,
    ) -> bool:
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """

        try:
            msg = self.__connection.recv_match(blocking = True, timeout = 1)

            if msg is None:
                self.__count += 1
                self.__local_logger.warning(f"No heartbeat received. Missing count: {self.__count}")
            else:
                self.__count = 0
                self.__local_logger.info("Heartbeat message received.")

            if self.__count >= 5:
                self.__status = "Disconnected"
            else:
                self.__status = "Connected"

            return True

        except Exception as e:
            self.__local_logger.error(f"Error in receiving message: {e}")
            return False


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
