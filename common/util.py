"""
Application utility module
"""

# Copyright 2021 Silicon Laboratories Inc. www.silabs.com
#
# SPDX-License-Identifier: Zlib
#
# The licensor of this software is Silicon Laboratories Inc.
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import argparse
import logging
import os.path
import socket
import sys
import threading
import time
import traceback
import bgapi
from bgapi.connector import ConnectorException
import serial.tools.list_ports

LOG_FORMAT = "%(levelname)s - %(message)s"
BT_XAPI = os.path.join(os.path.dirname(__file__), "../api/sl_bt.xapi")
BTMESH_XAPI = os.path.join(os.path.dirname(__file__), "../api/sl_btmesh.xapi")

class GenericApp():
    """ Generic application class. """
    def __init__(self, connection, apis):
        self.lib = bgapi.BGLib(connection, apis)
        self.log = logging.getLogger(str(type(self)))
        self._run = False

    def event_handler(self, evt):
        """ Public event handler to perform user actions. Meant to be overridden by child classes. """
        self.log.info("Received event: %s", evt)

    def _event_handler(self, evt):
        """ Private event handler to perform internal actions. """

    def run(self):
        """ Main execution loop of the application. """
        self._run = True
        exit_code = 0

        self.log.info("Open device")
        try:
            self.lib.open()
        except ConnectorException as err:
            self.log.error("%s", err)
            sys.exit(-1)
        # Reset device to get to a well defined state.
        self.reset()

        # Enter main program loop.
        while self._run:
            try:
                # The timeout is needed for Windows hosts to get the KeyboardInterrupt.
                # The timeout value is a tradeoff between CPU load and KeyboardInterrupt response time.
                # timeout=None: minimal CPU usage, KeyboardInterrupt not recognized until the next event.
                # timeout=0: maximal CPU usage, KeyboardInterrupt recognized immediately.
                # See the documentation of Queue.get method for details.
                evt = self.lib.get_event(timeout=0.1)
                if evt is not None:
                    self._event_handler(evt)
                    self.event_handler(evt)
            except bgapi.bglib.CommandFailedError as err:
                # Get additional info from trace.
                trace = traceback.extract_tb(sys.exc_info()[-1])[-3]
                self.log.error("%s", err)
                self.log.error("  File '%s', line %d, in %s", trace.filename, trace.lineno, trace.name)
                self.log.error("    %s", trace.line)
                self._run = False
                exit_code = -1
            except KeyboardInterrupt:
                self.log.info("User interrupt")
                self._run = False

        self.log.info("Close device")
        self.lib.close()
        sys.exit(exit_code)

    def stop(self):
        """ Terminate main execution loop. """
        self._run = False

    def reset(self):
        """ Reset device, meant to be overridden by child classes. """

class ConnectorApp(GenericApp):
    """ Generic application with automatic connector creation and argument parsing. """
    def __init__(self, apis, parser=None):
        if parser is None:
            parser = argparse.ArgumentParser()
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.epilog = (
            "examples:\n"
            "  %(prog)s                                   Try to autodetect serial port\n"
            "  %(prog)s COM4                              Open serial port on Windows\n"
            "  %(prog)s /dev/tty.usbmodem1234567890121    Open serial port on macOS\n"
            "  %(prog)s /dev/ttyACM0                      Open serial port on Linux\n"
            "  %(prog)s 192.168.1.10                      Open TCP port")
        parser.add_argument(
            "conn",
            nargs="?",
            help="Serial port or IPv4 address of the connection. Try to autodetect serial port if not provided.")
        parser.add_argument(
            "-l", "--log",
            type=str.upper,
            choices=logging._nameToLevel.keys(),
            help="Log level",
            default=logging.INFO
        )
        args = parser.parse_args()
        # Configure logging.
        logging.basicConfig(level=args.log, format=LOG_FORMAT)
        # Instantiate connection.
        try:
            self.connection = get_connector(args.conn)
        except AutoSelectError as err:
            logging.error("%s", err)
            logging.error("Please specify connection explicitly.")
            parser.print_usage()
            sys.exit(-1)
        # Call parent's constructor.
        super().__init__(self.connection, apis=apis)

class BluetoothApp(ConnectorApp):
    """ Application class for Bluetooth devices. """
    def __init__(self, apis=BT_XAPI, parser=None):
        self.address = None
        self.address_type = None
        super().__init__(apis, parser=parser)

    def _event_handler(self, evt):
        """ Internal Bluetooth event handler. """
        if evt == "bt_evt_system_boot":
            # Check Bluetooth stack version
            version = "{major}.{minor}.{patch}".format(**vars(evt))
            self.log.info("Bluetooth stack booted: v%s-b%s", version, evt.build)
            if version != self.lib.bt.__version__:
                self.log.warning("BGAPI version mismatch: %s (target) != %s (host)", version, self.lib.bt.__version__)
            # Get Bluetooth address
            _, self.address, self.address_type = self.lib.bt.system.get_identity_address()
            self.log.info("Bluetooth %s address: %s",
                "static random" if self.address_type else "public device",
                self.address)

    def reset(self):
        """ Reset Bluetooth device. """
        self.lib.bt.system.reset(self.lib.bt.system.BOOT_MODE_BOOT_MODE_NORMAL)

class BtMeshApp(ConnectorApp):
    """ Application class for Bluetooth mesh devices """
    def __init__(self, apis=[BT_XAPI, BTMESH_XAPI], parser=None):
        super().__init__(apis, parser=parser)
    
    def _event_handler(self, evt):
        """ Internal Bluetooth event handler. """
        if evt == "bt_evt_system_boot":
            # Check Bluetooth stack version
            version = "{major}.{minor}.{patch}".format(**vars(evt))
            self.log.info("Bluetooth stack booted: v%s-b%s", version, evt.build)
            if version != self.lib.bt.__version__:
                self.log.warning("BGAPI version mismatch: %s (target) != %s (host)", version, self.lib.bt.__version__)
            # Initialize Bluetooth Mesh device
            self.lib.btmesh.node.init()

    def reset(self):
        """ Reset for Bluetooth mesh device """
        self.lib.bt.system.reset(self.lib.bt.system.BOOT_MODE_BOOT_MODE_NORMAL)

class PeriodicTimer:
    """ Timer to call a target function periodically in the context of a separate thread. """
    def __init__(self, period, target=None, args=(), kwargs=None):
        self._period = float(period)
        self._target = target
        self._args = args
        if kwargs is None:
            kwargs = {}
        self._kwargs = kwargs
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = False

    def start(self):
        """ Start the timer. Must be called from the same thread as the stop method. """
        if self._started:
            # Timer has already been started.
            return
        if not self._thread.is_alive():
            self._thread.start()
        else:
            self._lock.release()
        self._started = True

    def stop(self):
        """ Stop the timer. """
        if not self._started:
            # Timer is not running.
            return
        self._lock.acquire()
        self._started = False

    def _run(self):
        """ The main loop of the timer thread. """
        while True:
            self._lock.acquire()
            self._lock.release()
            if self._target:
                self._target(*self._args, **self._kwargs)
            time.sleep(self._period)

class AutoSelectError(Exception):
    """ Error indicating automatic connector selection failure. """

def get_connector(conn=None):
    """
    Return a serial or socket connector instance.

    Try to autodetect serial device if no input is provided.
    This function is optimized for Silicon Labs development boards with default parameters.
    For non-default settings use the SerialConnector and SocketConnector constructors directly.
    """
    if conn is None:
        # Find Segger J-Link devices based on USB vendor ID.
        device_list = []
        for com in serial.tools.list_ports.comports():
            if com.vid == 0x1366:
                device_list.append(com.device)
        if len(device_list) == 0:
            raise AutoSelectError("No serial device found.")
        elif len(device_list) == 1:
            return bgapi.SerialConnector(device_list[0])
        else:
            devices = ", ".join(device_list)
            raise AutoSelectError("{} serial devices found: {}.".format(len(device_list), devices))
    else:
        connector_type = bgapi.SocketConnector
        try:
            # Check for a valid IPv4 address.
            socket.inet_aton(conn)
            # Append WSTK serial port number.
            conn = (conn, 4901)
        except OSError:
            # Assume serial port.
            connector_type = bgapi.SerialConnector
        return connector_type(conn)

def find_service_in_advertisement(adv_data, uuid):
    """ Find service with the given UUID in the advertising data. """
    if len(uuid) != 2 and len(uuid) != 16:
        raise ValueError("Invalid UUID length.")
    # Incomplete List of 16 or 128-bit  Service Class UUIDs.
    incomplete_list = 0x02 if len(uuid) == 2 else 0x06
    # Complete List of 16 or 128-bit  Service Class UUIDs.
    complete_list = 0x03 if len(uuid) == 2 else 0x07

    # Parse advertisement packet.
    i = 0
    while i < len(adv_data):
        ad_field_length = adv_data[i]
        ad_field_type = adv_data[i + 1]
        # Find AD types of interest.
        if ad_field_type in (incomplete_list, complete_list):
            ad_uuid_count = int((ad_field_length - 1) / len(uuid))
            # Compare each UUID to the service UUID to be found.
            for j in range(ad_uuid_count):
                start_idx = i + 2 + j*len(uuid)
                # Get UUID from AD data.
                ad_uuid = adv_data[start_idx: start_idx + len(uuid)]
                if ad_uuid == uuid:
                    return True
        # Advance to the next AD structure.
        i += ad_field_length + 1
    # UUID not found.
    return False
