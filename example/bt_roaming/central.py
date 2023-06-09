#!/usr/bin/env python3
""" Roaming NCP-host Example Application for central devices.
"""

# Copyright 2022 Silicon Laboratories Inc. www.silabs.com
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

import json
import logging
import os
import queue
import sys
import time
import threading
import bgapi

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from common.util import ArgumentParser, BluetoothApp, get_connector, find_service_in_advertisement

# Virtual identity address of the access points
IDENTITY_ADDRESS = "DE:AD:BE:EF:12:34"
# Service UUID of interest: heart rate
GATT_SERVICE_UUID = b"\x0d\x18"
# Characteristic UUID of interest: heart rate measurement
GATT_CHARACTERISTIC_UUID = b"\x37\x2a"
# The maximum number of connections has to match with the configuration on the target side.
SL_BT_CONFIG_MAX_CONNECTIONS = 4
# Wait for boot event of an access point for this amount of time in seconds
BOOT_TIMEOUT = 2
# BLE connection attempts are aborted after this amount of time in seconds
CONNECTION_TIMEOUT = 3
# Duration of the scanning during device discovery in seconds
SCANNING_TIMEOUT = 3
# Time period of the periodic device discovery in seconds
DISCOVERY_PERIOD = 30
# Time between RSSI measurements in seconds
RSSI_MEASUREMENT_PERIOD = 10
# Connection is closed if connection RSSI value drops below this value in dBm
# A value of -127 or smaller means that the threshold is turned off.
RSSI_DISCONNECT_THRESHOLD = -127
# Path of the bonding database file
BONDING_DB_PATH = "bonding_db.json"

class AccessPoint(BluetoothApp):
    """ Roaming Access Point """
    def __init__(self,
                 connector,
                 event_queue: queue.Queue,
                 identity_address=None,
                 identity_type=None):
        self._event_queue = event_queue
        self._identity_address = identity_address
        self._identity_type = identity_type
        self.ready = threading.Event()
        self.connections = {}
        self._rssi_thread = threading.Thread(target=self._rssi_task, daemon=True)
        self._rssi_thread.start()
        super().__init__(connector)

    def start_scan(self):
        """ Start scanning """
        self.lib.bt.scanner.start(
            self.lib.bt.scanner.SCAN_PHY_SCAN_PHY_1M,
            self.lib.bt.scanner.DISCOVER_MODE_DISCOVER_GENERIC)

    def stop_scan(self):
        """ Stop scanning """
        self.lib.bt.scanner.stop()

    def connectable(self):
        """ Check if new connections can be established """
        return len(self.connections) < SL_BT_CONFIG_MAX_CONNECTIONS

    def connect(self, address, address_type=None, bonding_data=None):
        """ Connect to a device """
        if not self.connectable():
            raise Exception("no more connection possible")
        if address_type is None:
            address_type = self.lib.bt.gap.ADDRESS_TYPE_PUBLIC_ADDRESS
        if bonding_data is None:
            bonding_data = {}
        _, connection = self.lib.bt.connection.open(
            address,
            address_type,
            self.lib.bt.gap.PHY_PHY_1M)
        self.connections[connection] = {"address": address,
                                        "address_type": address_type,
                                        "bonding_data": bonding_data,
                                        "opened": threading.Event()}
        if not self.connections[connection]["opened"].wait(timeout=CONNECTION_TIMEOUT):
            self.log.warning(f"failed to open connection to {address}")
            self.lib.bt.connection.close(connection)

    def _rssi_task(self):
        """ Monitor connection RSSI """
        while True:
            for conn in self.connections:
                try:
                    self.lib.bt.connection.get_rssi(conn)
                except bgapi.bglib.CommandFailedError:
                    pass
            time.sleep(RSSI_MEASUREMENT_PERIOD)

    def event_handler(self, evt):
        """ Bluetooth event handler """
        # Forward all events to the network coordinator
        self._event_queue.put((self.id, evt))

    # Common event callbacks
    def bt_evt_system_boot(self, evt):
        """ Bluetooth event callback """
        # Check if external bonding database feature is available on the target
        try:
            self.lib.bt.sm.get_bonding_handles(0)
            self.log.error("External bonding database feature missing from the target firmware.")
            self.stop()
            return
        except bgapi.bglib.CommandFailedError as err:
            if err.errorcode != 0xe: # Tolerate only 'feature not available' error
                raise
        if self._identity_address is not None:
            if self._identity_type is None:
                self._identity_type = self.lib.bt.gap.ADDRESS_TYPE_PUBLIC_ADDRESS
            self.lib.bt.gap.set_identity_address(self._identity_address, self._identity_type)
        self.lib.bt.sm.set_bondable_mode(1)
        self.ready.set()

    def bt_evt_connection_opened(self, evt):
        """ Bluetooth event callback """
        self.log.info(f"Connection opened: {evt.address}")
        self.connections[evt.connection]["opened"].set()

    def bt_evt_connection_closed(self, evt):
        """ Bluetooth event callback """
        self.log.info(f"Connection closed: {self.connections[evt.connection]['address']}")
        del self.connections[evt.connection]

    def bt_evt_connection_rssi(self, evt):
        """ Bluetooth event callback """
        address = self.connections[evt.connection]["address"]
        if evt.status != 0:
            self.log.error(f"RSSI [{address}] failed: 0x{evt.status:02x}")
            return
        self.log.info(f"RSSI [{address}]: {evt.rssi} dBm")
        if evt.rssi < RSSI_DISCONNECT_THRESHOLD:
            self.log.info("RSSI threshold reached, close connection")
            self.lib.bt.connection.close(evt.connection)

    def bt_evt_connection_parameters(self, evt):
        """ Bluetooth event callback """
        if evt.security_mode != 0:
            # Successfully bonded
            # Start GATT discovery with finding the service handle
            self.lib.bt.gatt.discover_primary_services_by_uuid(
                evt.connection,
                GATT_SERVICE_UUID)

    def bt_evt_sm_bonding_failed(self, evt):
        """ Bluetooth event callback """
        address = self.connections[evt.connection]["address"]
        self.log.error(f"Bonding with {address} failed with reason 0x{evt.reason:x}")

    # External bonding database event callbacks
    def bt_evt_external_bondingdb_data_request(self, evt):
        """ Bluetooth event callback """
        # 0 length data means that the data is not available in the external bonding DB
        data = self.connections[evt.connection]["bonding_data"].get(evt.type, b"")
        self.lib.bt.external_bondingdb.set_data(evt.connection, evt.type, data)

    def bt_evt_external_bondingdb_data(self, evt):
        """ Bluetooth event callback """
        self.connections[evt.connection]["bonding_data"][evt.type] = evt.data

    def bt_evt_external_bondingdb_data_ready(self, evt):
        """ Bluetooth event callback """
        # Initiate bonding
        self.lib.bt.sm.increase_security(evt.connection)

    # GATT event callbacks
    def bt_evt_gatt_service(self, evt):
        """ Bluetooth event callback """
        # Store service handle for the connection
        self.connections[evt.connection]["service"] = evt.service

    def bt_evt_gatt_characteristic(self, evt):
        """ Bluetooth event callback """
        # Store characteristic handle for the connection
        self.connections[evt.connection]["characteristic"] = evt.characteristic

    def bt_evt_gatt_procedure_completed(self, evt):
        """ Bluetooth event callback """
        if evt.result != 0:
            self.log.error(f"GATT procedure completed with status 0x{evt.result:04x}")
            return
        if "characteristic" not in self.connections[evt.connection].keys():
            # Continue GATT discovery with finding the characteristic handle
            self.lib.bt.gatt.discover_characteristics_by_uuid(
                evt.connection,
                self.connections[evt.connection]["service"],
                GATT_CHARACTERISTIC_UUID)
        elif "notification" not in self.connections[evt.connection].keys():
            # Finally, request notification for the characteristic
            self.lib.bt.gatt.set_characteristic_notification(
                evt.connection,
                self.connections[evt.connection]["characteristic"],
                self.lib.bt.gatt.CLIENT_CONFIG_FLAG_NOTIFICATION)
            self.connections[evt.connection]["notification"] = True

    def bt_evt_gatt_characteristic_value(self, evt):
        """ Bluetooth event callback """
        process_characteristic_value(self, evt)

class NetworkCoordinator():
    """ Roaming network coordinator managing multiple access points """
    def __init__(self, connectors):
        self._event_queue = queue.Queue()
        self._start_discovery = threading.Event()
        self._scan_result = {}
        self._bonding_db = load_bonding_db()
        self._bonding_db_dirty = threading.Event()
        self.ap_dict = {}
        for connector in connectors:
            ap = AccessPoint(connector,
                             self._event_queue,
                             identity_address=IDENTITY_ADDRESS)
            self.ap_dict[ap.id] = ap
        self.log = logging.getLogger(type(self).__name__)
        self._t1 = threading.Thread(target=self.event_handler, daemon=True)
        self._t2 = threading.Thread(target=self.discovery_scheduler, daemon=True)
        self._t3 = threading.Thread(target=self.discovery_task, daemon=True)
        self._t4 = threading.Thread(target=self.bonding_db_task, daemon=True)

    def start(self):
        """ Start access points and wait for boot event, start worker threads """
        for ap in self.ap_dict.values():
            ap.start()
        for ap in self.ap_dict.values():
            if not ap.ready.wait(timeout=BOOT_TIMEOUT):
                raise Exception(f"AP#{ap.id} failed to boot")
        self.log.info("all access points booted")
        self._t1.start()
        self._t2.start()
        self._t3.start()
        self._t4.start()

    def stop(self):
        """ Stop all access points. """
        for ap in self.ap_dict.values():
            ap.stop()

    def discover(self):
        """ Scan for and connect to devices. """
        # clear scan result
        self._scan_result = {}
        self.log.info("discover devices...")
        # select only connectable access points for scanning
        scan_ap_list = [ap for ap in self.ap_dict.values() if ap.connectable()]
        for ap in scan_ap_list:
            ap.start_scan()
        time.sleep(SCANNING_TIMEOUT)
        for ap in scan_ap_list:
            ap.stop_scan()
        if len(self._scan_result) == 0:
            self.log.info("no devices found")
        else:
            self.log.info("device(s) found:")
            self.log.info(self._scan_result)
        for address, result in self._scan_result.items():
            # find access point with the largest RSSI value
            ap_id = max(result["rssi"], key=result["rssi"].get)
            self.ap_dict[ap_id].connect(
                address=address,
                address_type=result["address_type"],
                bonding_data=self.get_bonding_data(address))

    def update_scan_result(self, ap_id, evt):
        """ Collect scan report events from various access points. """
        if evt.address not in self._scan_result.keys():
            self._scan_result[evt.address] = {"address_type": evt.address_type, "rssi": {}}
        # New RSSI value overwrites old one (i.e. no averaging)
        self._scan_result[evt.address]["rssi"][ap_id] = evt.rssi

    def get_bonding_data(self, address):
        """ Provide bonding data for connection """
        if address not in self._bonding_db.keys():
            # Create bonding data entry if not available yet
            self._bonding_db[address] = {}
        return self._bonding_db[address]

    def event_handler(self):
        """ Handle events from all access points """
        while True:
            try:
                # Timeout is needed for Windows hosts to get the KeyboardInterrupt in the main thread.
                ap_id, evt = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if evt in ["bt_evt_scanner_legacy_advertisement_report", "bt_evt_scanner_scan_report"]:
                if scan_filter(evt):
                    self.update_scan_result(ap_id, evt)
            elif evt == "bt_evt_connection_closed":
                # Start device discovery immediately when a device disconnects
                self._start_discovery.set()
            elif evt == "bt_evt_external_bondingdb_data":
                # Bonding database has changed
                self._bonding_db_dirty.set()

    def discovery_scheduler(self):
        """ Schedule discovery process periodically """
        while True:
            self._start_discovery.set()
            time.sleep(DISCOVERY_PERIOD)

    def discovery_task(self):
        """ Check for discovery request """
        while True:
            self._start_discovery.wait()
            self._start_discovery.clear()
            self.discover()

    def bonding_db_task(self):
        """ Check if bonding database needs to be saved """
        while True:
            self._bonding_db_dirty.wait()
            # Delay writing to file to avoid too frequent file access
            time.sleep(1)
            self._bonding_db_dirty.clear()
            save_bonding_db(self._bonding_db)

def scan_filter(evt):
    """ Filter for selecting devices of interest """
    return find_service_in_advertisement(evt.data, GATT_SERVICE_UUID)

def process_characteristic_value(ap: AccessPoint, evt):
    """ Process characteristic notification events """
    value = int(evt.value[1])
    address = ap.connections[evt.connection]["address"]
    ap.log.info(f"heart rate [{address}]: {value} BPM")

def load_bonding_db():
    """ Load bonding database from file """
    if not os.path.exists(BONDING_DB_PATH):
        return {}
    with open(BONDING_DB_PATH, "r") as bonding_db:
        db_in = json.load(bonding_db)
        db_out = {}
        for address, data in db_in.items():
            db_out[address] = {int(key): bytes.fromhex(value) for key, value in data.items()}
        return db_out

def save_bonding_db(db_in: dict):
    """ Save bonding database to file """
    db_out = {}
    for address, data in db_in.items():
        db_out[address] = {key: value.hex() for key, value in data.items()}
    with open(BONDING_DB_PATH, "w") as bonding_db:
        json.dump(db_out, bonding_db)

def main():
    """ Main function. """
    parser = ArgumentParser(description=__doc__, single_mode=False)
    parser.add_argument(
        "-d",
        action="store_true",
        help="Delete bondings")
    args = parser.parse_args()
    connectors = get_connector(args)
    if args.d:
        # Delete bonding database file if exists
        try:
            os.remove(BONDING_DB_PATH)
        except FileNotFoundError:
            pass
    app = NetworkCoordinator(connectors)
    app.start()
    # Catch KeyboardInterrupt
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        app.stop()

# Script entry point.
if __name__ == "__main__":
    main()
