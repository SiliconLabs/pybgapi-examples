#!/usr/bin/env python3
"""
Temperature Measurement NCP-host Example Application.
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
import os.path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from common.conversion import Ieee11073Float
from common.util import BluetoothApp, PeriodicTimer

# Constants
# Unit definitions for temperature measurement
TEMPERATURE_UNIT_CELSIUS = b"\x00"
TEMPERATURE_UNIT_FAHRENHEIT = b"\x01"
# Temperature measurement characteristic indication period in seconds
INDICATION_PERIOD = 1.0
# Characteristic values
GATTDB_DEVICE_NAME = b"Thermometer Example"
GATTDB_MANUFACTURER_NAME_STRING = b"Silicon Labs"
GATTDB_TEMPERATURE_TYPE = b"\x02" # Body

class App(BluetoothApp):
    """ Application derived from generic BluetoothApp. """
    def event_handler(self, evt):
        """ Override default event handler of the parent class. """
        # This event indicates the device has started and the radio is ready.
        # Do not call any stack command before receiving this boot event!
        if evt == "bt_evt_system_boot":
            self.timer = PeriodicTimer(period=INDICATION_PERIOD, target=self.send_indication)
            self.adv_handle = None
            self.temperature = 0
            self.gattdb_init()
            self.adv_start()

        # This event indicates that a new connection was opened.
        elif evt == "bt_evt_connection_opened":
            print("Connection opened")

        # This event indicates that a connection was closed.
        elif evt == "bt_evt_connection_closed":
            self.timer.stop()
            print("Connection closed")
            self.adv_start()

        # Events triggered by the remote GATT client.
        elif evt == "bt_evt_gatt_server_characteristic_status":
            if evt.characteristic == self.gattdb_temperature_measurement:
                if evt.status_flags == self.lib.bt.gatt_server.CHARACTERISTIC_STATUS_FLAG_CLIENT_CONFIG:
                    # The remote client requested the status change.
                    if evt.client_config_flags == self.lib.bt.gatt_server.CLIENT_CONFIGURATION_DISABLE:
                        print("Indication disabled.")
                        self.timer.stop()
                    else:
                        print("Indication enabled.")
                        self.timer.start()
                elif evt.status_flags == self.lib.bt.gatt_server.CHARACTERISTIC_STATUS_FLAG_CONFIRMATION:
                    print("    indication sent.")

    def gattdb_init(self):
        """ Initialize GATT database. """
        _, session = self.lib.bt.gattdb.new_session()

        # Generic Access
        _, service = self.lib.bt.gattdb.add_service(
            session,
            self.lib.bt.gattdb.SERVICE_TYPE_PRIMARY_SERVICE,
            0,
            b"\x00\x18"
        )
        # Device Name
        self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_READ |
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_WRITE,
            0,
            0,
            b"\x00\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            len(GATTDB_DEVICE_NAME),
            GATTDB_DEVICE_NAME
        )
        # Appearance
        self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_READ,
            0,
            0,
            b"\x01\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            2,
            b"\x00\x00"
        )
        self.lib.bt.gattdb.start_service(session, service)

        # Device Information
        _, service = self.lib.bt.gattdb.add_service(
            session,
            self.lib.bt.gattdb.SERVICE_TYPE_PRIMARY_SERVICE,
            0,
            b"\x0A\x18"
        )
        # Manufacturer Name String
        self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_READ,
            0,
            0,
            b"\x29\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            len(GATTDB_MANUFACTURER_NAME_STRING),
            GATTDB_MANUFACTURER_NAME_STRING
        )
        # System ID
        # Pad and reverse unique ID to get System ID.
        addr = self.address.split(":")
        system_id = bytes.fromhex("".join(addr[:3] + ["ff", "fe"] + addr[3:]))
        self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_READ,
            0,
            0,
            b"\x23\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            8,
            system_id
        )
        self.lib.bt.gattdb.start_service(session, service)

        # Health Thermometer
        _, service = self.lib.bt.gattdb.add_service(
            session,
            self.lib.bt.gattdb.SERVICE_TYPE_PRIMARY_SERVICE,
            self.lib.bt.gattdb.SERVICE_PROPERTY_FLAGS_ADVERTISED_SERVICE,
            b"\x09\x18"
        )
        # Temperature Measurement
        _, self.gattdb_temperature_measurement = self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_INDICATE,
            0,
            0,
            b"\x1C\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            5,
            b"\x00"*5
        )
        # Temperature Type
        self.lib.bt.gattdb.add_uuid16_characteristic(
            session,
            service,
            self.lib.bt.gattdb.CHARACTERISTIC_PROPERTIES_CHARACTERISTIC_READ,
            0,
            0,
            b"\x1D\x2A",
            self.lib.bt.gattdb.VALUE_TYPE_FIXED_LENGTH_VALUE,
            len(GATTDB_TEMPERATURE_TYPE),
            GATTDB_TEMPERATURE_TYPE
        )
        self.lib.bt.gattdb.start_service(session, service)

        self.lib.bt.gattdb.commit(session)

    def adv_start(self):
        """ Start advertising. """
        if self.adv_handle is None:
            # Create advertising set for the first call.
            _, self.adv_handle = self.lib.bt.advertiser.create_set()
            # Set advertising interval to 100 ms.
            self.lib.bt.advertiser.set_timing(
                self.adv_handle,
                160,  # interval min
                160,  # interval max
                0,    # duration
                0)    # max events
        self.lib.bt.advertiser.start(
            self.adv_handle,
            self.lib.bt.advertiser.DISCOVERY_MODE_GENERAL_DISCOVERABLE,
            self.lib.bt.advertiser.CONNECTION_MODE_CONNECTABLE_SCANNABLE)

    def send_indication(self):
        """ Send indication with dummy temperature data. """
        print("Sending {} C...".format(self.temperature))

        # Convert temperature value.
        value = TEMPERATURE_UNIT_CELSIUS + Ieee11073Float(self.temperature).to_bytes()
        self.lib.bt.gatt_server.notify_all(self.gattdb_temperature_measurement, value)

        # Increment dummy temperature data.
        self.temperature += 1
        if self.temperature > 25:
            self.temperature = 0

# Script entry point.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    # Instantiate the application.
    app = App(parser=parser)
    # Running the application blocks execution until it terminates.
    app.run()
