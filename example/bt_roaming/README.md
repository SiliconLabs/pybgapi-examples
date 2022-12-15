# Bluetooth - Roaming

This example is like the `bt_thermometer_client` - `bt_thermometer`  example pair with multi-radio
support and bonding. The `central.py` script corresponds to the `bt_thermometer_client` and acts
as a virtual access point made of several radios. The `peripheral.py` script corresponds to the
`bt_thermometer` example and implements multiple heart rate sensors at once.

Each radio board in the `central.py` forms a physical access point. The access points are managed
by a single network coordinator. Scanning for heart rate sensors is performed for 3 seconds in every
30 seconds or immediately when a device disconnects. When a heart rate sensor is found, the nearest
AP (i.e. the one with the largest RSSI) connects to it. Every AP uses the same identity. I.e., all
heart rate sensors seem to be connected to the same virtual access point.

Bonding is performed by the access points using external bonding database feature. This means that
the user application is responsible for storing the bonding keys provided by the Bluetooth stack and
provide those keys when requested by the stack. In this example, bonding data is stored in a json
file between sessions.

Bonding keys are sensitive data therefore both the bonding data storage file and the NCP
communication between the host SW and the target FW shall be encrypted when developing products that
use the external bonding database feature.

The external bonding database Bluetooth feature is not part of the **Bluetooth - NCP** example by
default, it has to be added manually when creating the project for the access points. Heart rate
sensor devices shall be used with the default **Bluetooth - NCP** example without external bonding
database.
