"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)

QUEUE_MAX_SIZE = 1

# Set worker counts

WORKER_COUNT = 1

# Any other constants

SENDER_PERIOD = 1
TARGET = command.Position(10, 20, 30)

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller

    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues

    mp_manager = mp.Manager()

    # Create queues

    telemetry_to_command = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, QUEUE_MAX_SIZE)
    command_to_main = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, QUEUE_MAX_SIZE)
    receiver_to_main = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, QUEUE_MAX_SIZE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender

    result, heartbeat_sender_properties = worker_manager.WorkerProperties.create(
        WORKER_COUNT,
        heartbeat_sender_worker.heartbeat_sender_worker,
        (connection, SENDER_PERIOD,),
        [],
        [],
        controller,
        main_logger
    )

    if not result:
        main_logger.error("Unable to create Heartbeat Sender properties")
        return -1

    assert heartbeat_sender_properties is not None

    # Heartbeat receiver

    result, heartbeat_receiver_properties = worker_manager.WorkerProperties.create(
        WORKER_COUNT,
        heartbeat_receiver_worker.heartbeat_receiver_worker,
        (connection,),
        [],
        [receiver_to_main],
        controller,
        main_logger
    )

    if not result:
        main_logger.error("Unable to create Heartbeat Receiver properties")
        return -1

    assert heartbeat_receiver_properties is not None

    # Telemetry

    result, telemetry_properties = worker_manager.WorkerProperties.create(
        WORKER_COUNT,
        telemetry_worker.telemetry_worker,
        (connection,),
        [],
        [telemetry_to_command],
        controller,
        main_logger
    )

    if not result:
        main_logger.error("Unable to create Telemetry properties")
        return -1

    assert telemetry_properties is not None

    # Command

    result, command_properties = worker_manager.WorkerProperties.create(
        WORKER_COUNT,
        command_worker.command_worker,
        (connection, TARGET,),
        [telemetry_to_command],
        [command_to_main],
        controller,
        main_logger
    )

    if not result:
        main_logger.error("Unable to create Command properties")
        return -1

    assert command_properties is not None

    # Create the workers (processes) and obtain their managers

    worker_managers = []

    result, heartbeat_sender_manager = worker_manager.WorkerManager.create(
        heartbeat_sender_properties,
        main_logger,
    )

    if not result:
        main_logger.error("Unable to create manager for Heartbeat Sender")
        return -1

    assert heartbeat_sender_manager is not None
    worker_managers.append(heartbeat_sender_manager)

    result, heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        heartbeat_receiver_properties,
        main_logger,
    )

    if not result:
        main_logger.error("Unable to create manager for Heartbeat Receiver")
        return -1

    assert heartbeat_receiver_manager is not None
    worker_managers.append(heartbeat_receiver_manager)

    result, telemetry_manager = worker_manager.WorkerManager.create(
        telemetry_properties,
        main_logger,
    )

    if not result:
        main_logger.error("Unable to create manager for Telemetry")
        return -1

    assert telemetry_manager is not None
    worker_managers.append(telemetry_manager)

    result, command_manager = worker_manager.WorkerManager.create(
        command_properties,
        main_logger,
    )

    if not result:
        main_logger.error("Unable to create manager for Command")
        return -1

    assert command_manager is not None
    worker_managers.append(command_manager)

    # Start worker processes

    for manager in worker_managers:
        manager.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects

    start_time = time.time()
    drone_connected = True

    while time.time() - start_time < 100 and drone_connected:
        try:
            heartbeat_status = receiver_to_main.queue.get()

            if heartbeat_status == "Disconnected":
                drone_connected = False
                main_logger.info("Drone Disconnected, stopping loop")
                break

        except queue.Empty:
            main_logger.error("Receiver to Main Queue is empty, no reading")
            continue

        try:
            command_status = command_to_main.queue.get()

            if command_status is not None:
                main_logger.info(f"Command read: {command_status}")

        except queue.Empty:
            main_logger.error("Command to Main Queue is empty, no reading")

        time.sleep(0.1)


    # Stop the processes

    controller.request_exit()

    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START

    command_to_main.fill_and_drain_queue()
    telemetry_to_command.fill_and_drain_queue()
    receiver_to_main.fill_and_drain_queue()

    main_logger.info("Queues cleared")

    # Clean up worker processes

    for manager in worker_managers:
        manager.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance

    controller.clear_exit()

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
