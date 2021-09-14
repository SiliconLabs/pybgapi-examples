# PyBGAPI Examples

This repo contains example projects based on [pyBGAPI](https://pypi.org/project/pybgapi/) that
implement simple Bluetooth and Bluetooth mesh applications for demonstration purposes.
These examples can be used as references to implement custom Bluetooth and Bluetooth mesh
applications in Python in just a few minutes without writing a single line of embedded code.

## TL;DR

1. Install pyBGAPI.
    ```
    pip install pybgapi
    ```

2. Flash the **Bluetooth - NCP** or **Bluetooth Mesh - NCP Empty** demo binary on your [Wireless Development Kit](https://www.silabs.com/development-tools/wireless)
    using [Simplicity Studio](https://www.silabs.com/developers/simplicity-studio).

3. Run an arbitrary example from the repo.
    ```
    python3 example/empty/app.py
    ```
    or
    ```
    python3 example/btmesh_empty/app.py
    ```

## Getting Started

To get started with Silicon Labs Bluetooth software, see
[QSG169: Bluetooth® SDK v3.x Quick Start Guide](https://www.silabs.com/documents/public/quick-start-guides/qsg169-bluetooth-sdk-v3x-quick-start-guide.pdf).
For Bluetooth Mesh, see
[QSG176: Bluetooth® Mesh SDK v2.x Quick-Start Guide](https://www.silabs.com/documents/public/quick-start-guides/qsg176-bluetooth-mesh-sdk-v2x-quick-start-guide.pdf).

In the NCP context, the application runs on a host MCU or a PC, which is the NCP Host, while the
Bluetooth stack runs on an EFR32, which is the NCP Target.

The NCP Host and Target communicate via a serial interface (UART). The communication between the NCP
Host and Target is defined in the Silicon Labs proprietary protocol, BGAPI. pyBGAPI is the reference
implementation of the BGAPI protocol in Python for the NCP Host.

[AN1259: Using the v3.x Silicon Labs Bluetooth® Stack in Network CoProcessor Mode](https://www.silabs.com/documents/public/application-notes/an1259-bt-ncp-mode-sdk-v3x.pdf)
provides a detailed description how NCP works and how to configure it for custom hardware.

For latest BGAPI documentation, see [docs.silabs.com](https://docs.silabs.com/bluetooth/latest/).

## Generic Application Classes

All example applications in this repo are based on the generic application classes. These classes
are defined in [util.py](common/util.py) and provide all the common code that the example
applications share. Therefore, the user code contains only the bare minimum without duplication.
It also makes writing a custom event-driven application quite simple. The application classes have
a multi level inheritance chain, where each inheritance level adds extra features and becomes more
specialized.

### GenericApp

This class provides the skeleton for all application classes. It is responsible for connecting to an
NCP Target and receiving the events in an infinite loop.

Its constructor instantiates one `BGLib` object, which is accessible in its `lib` attribute. This
`lib` object is the interface for sending BGAPI commands to the target.

The execution of the application starts by calling the `run` method. This method opens the
connection (e.g., the serial port of a WSTK board), performs a reset to get to a well defined
state, and receives events from the NCP Target in an infinite loop. The event reception happens
in a blocking manner without timeout. It also implies that the `run` method is a synchronous call,
i.e., the execution of the script will continue when the running terminates. If the running
terminates for one of the following reason, the connection will be closed and the script execution
continues:
- User interruption with the `Ctrl` + `C` keys.
- Programmatically calling the `stop` method.
- Upon BGAPI command failure.

### ConnectorApp

This class extends the *GenericApp* with logging, CLI argument parsing and automatic connector
creation. The connector is initialized with the default connection parameters. Therefore, this class
is optimal for Silicon Labs development kits. Adjustments might be necessary for custom boards.

Invoke the help message of the examples to get detailed information about the CLI options.
```
python3 example/empty/app.py -h
```

### BluetoothApp

This class extends the *ConnectorApp* with the following features.

#### Check BGAPI Version

Every Bluetooth SDK comes with an XAPI file that describes the actual version of the BGAPI protocol.
This repo contains a copy of the XAPI file. The examples are written based on this copy. The BGAPI
version on the host and target side should be aligned. Otherwise, unexpected issues may happen.
Upon boot event, the version of the XAPI file and the Bluetooth stack version running on the NCP
Target are compared and a warning message is printed if a mismatch occurs.

#### Print Bluetooth Address

Upon boot event, the Bluetooth address is read from the NCP Target and printed on the console.
The address is also cached in the `address` and `address_type` attributes, so it can be accessed
later without NCP communication overhead.

#### Implement Soft Reset

The *BluetoothApp* overrides the empty `reset` method of the *GenericApp* that is called by the
`run` method. When called, the device will restart in normal boot mode.

#### Default XAPI File

The *BluetoothApp* uses the [sl_bt.xapi](api/sl_bt.xapi) file by default in its constructor.

### BtMeshApp

This class extends the *ConnectorApp* with the following features.

#### Check BGAPI Version

Every Bluetooth SDK comes with an XAPI file that describes the actual version of the BGAPI protocol.
This repo contains a copy of the XAPI file. The examples are written based on this copy. The BGAPI
version on the host and target side should be aligned. Otherwise, unexpected issues may happen.
Upon boot event, the version of the XAPI file and the Bluetooth stack version running on the NCP
Target are compared and a warning message is printed if a mismatch occurs.

#### Initialize Mesh Node

Initializes the Bluetooth mesh stack in Node role. When initialization is complete, a node initialized
event will be generated. This command must be issued before any other Bluetooth mesh commands.
Note that you may initialize a device either in the Provisioner or the Node role, but not both.

#### Implement Soft and Node Reset

The *BtMeshApp* overrides the empty `reset` method of the *GenericApp* that is called by the
`run` method. When called, the device will restart in normal boot mode without any previous node 
configuration parameters. I.e., if the node was previously provisioned into a network, it will be
removed.

#### Default XAPI File

The *BtMeshApp* uses both the Bluetooth [sl_bt.xapi](api/sl_bt.xapi) and Bluetooth mesh
[sl_btmesh.xapi](api/sl_btmesh.xapi) XAPI files by default in its constructor.

## Examples

All examples in this repo reproduce the behavior of existing C examples from the GSDK.
The examples can be tested together with the [EFR Connect](https://www.silabs.com/developers/efr-connect-mobile-app)
mobile app.
See the documentation of the original C examples to get more information.

### [Bluetooth - Empty](example/empty/app.py)

Original C example: **Bluetooth - SoC Empty**

This example is ***almost*** empty. It implements a basic application to demonstrate how to handle
events and how to use the GATT database.

* A simple application is implemented in the event handler function that starts advertising on boot
    (and on *connection_closed* event). As a result, remote devices can find the device and connect
    to it.

* A simple GATT database is defined by adding Generic Access and Device Information services. As a
    result, remote devices can read basic information, such as the device name.

### [Bluetooth - iBeacon](example/ibeacon/app.py)

Original C example: **Bluetooth - SoC iBeacon**

An [iBeacon]((https://developer.apple.com/ibeacon/)) device is an implementation that sends
non-connectable advertisements in iBeacon format.
The iBeacon Service gives Bluetooth accessories a simple and convenient way to send iBeacon to
smartphones.

### [Bluetooth - Thermometer](example/thermometer/app.py)

Original C example: **Bluetooth - SoC Thermometer**

This example implements the [Health Thermometer Service](https://www.bluetooth.com/specifications/specs/health-thermometer-service-1-0/).
It enables a peer device to connect and receive temperature values via Bluetooth.

The NCP Host has no access to the board peripherals, only to the Bluetooth stack via BGAPI.
Therefore, neither the button nor the temperature sensor is available in this example. The
temperature measurement values are just dummy values for demo purposes.

### [Bluetooth - Thermometer Client](example/thermometer_client/app.py)

Original C example: **Bluetooth - SoC Thermometer Client**

This example application demonstrates the operation of a client device in a multi-slave BLE
topology. Silicon Labs Bluetooth stack supports simultaneous connection for up to eight slave
devices at a time. This sample application illustrates how to handle simultaneous connection
to four thermometer peripheral devices.

### [Bluetooth mesh - Empty](example/btmesh_empty/app.py)

Original C example: **Bluetooth Mesh - SoC Empty**

This example demonstrates the bare minimum needed for a Bluetooth Mesh Network Co-Processor
application. The application establishes connection with the target device according to the
parameters provided at application launch, starts Unprovisioned Device Beaconing after boot
and can be provisioned to a Mesh Network.
This Software Example can be used as a starting point for a python host project and can be
extended according to application requirements, utilizing the whole set of pyBGAPI events
and commands.

## Creating a Custom Application

To create a custom Bluetooth application, follow these steps:
- Import the [util.py](common/util.py) module.
- Create your own application class inherited from the `BluetoothApp` class.
- Override its `event_handler` method.
- Instantiate your application class.
- Call its `run` method.

## Troubleshooting

### BGAPI Version Mismatch

#### Observed Behavior

The example prints a warning message, as follows:
```
WARNING - BGAPI version mismatch: 3.2.1 (target) != 3.2.2 (host)
```

#### Explanation

The examples are written based on a given BGAPI version. This repo contains a copy of the XAPI
descriptor file of this version. The Bluetooth stack running on the NCP Target has its own BGAPI
version too. It's the developer's responsibility to keep the BGAPI version on both the target and
the host side in sync. Otherwise, the correct behavior cannot be guaranteed.

Difference in the patch version most probably won't cause any issues, while difference in the major
version most probably will.

Also note that the pyBGAPI is more sensitive to the API deprecations, because unlike the C
implementation of the BGAPI, it has no compatibility layer.

#### Solution

1. Update the Bluetooth SDK in the Simplicity Studio and Flash the **Bluetooth - NCP** demo example
on your Wireless Development Kit.

2. Use the XAPI file from the Bluetooth SDK and update your application script accordingly. The
XAPI file can be found at */path/to/sdks/gecko_sdk_suite/v3.x/protocol/bluetooth/api/sl_bt.xapi*

3. If only the patch versions differ, the warning message can be ignored.

### 'NCP' vs. 'NCP Empty'

#### Observed Behavior

The execution stops after an error message like this is printed:
```
Received message 'bt_rsp_gattdb_new_session' with parameter(s) 'session' missing.
Command returned 'result' parameter with non-zero errorcode: 0xf
  File 'example/empty/app.py', line 65, in gattdb_init
    _, session = self.lib.bt.gattdb.new_session()
```

#### Explanation

The error code `0xf` means that the feature is not supported and refers to the Bluetooth dynamic
GATT database feature. Most likely, the root case is that the *Bluetooth - NCP Empty* has been
flashed on the target instead of the *Bluetooth - NCP*. The difference is that the *NCP Empty*
example contains an ***almost*** empty static GATT database, while the *NCP* contains no static
GATT database at all, but the dynamic GATT database feature instead. The dynamic GATT database
feature makes it possible to configure the GATT database entirely from the host side. The
examples in this repo utilize this feature.

#### Solution

Flash the **Bluetooth - NCP** example on your development board.

### app.run() Blocks the Script from Executing

#### Observed Behavior

Code after app.run() call executes only after the app terminates.

#### Explanation

The *GenericApp* class has been designed as a standalone event-driven application. The way to
extend this application with custom business logic depends on the actual use case.

#### Solution

1. For periodic tasks (e.g., polling a sensor periodically) the *PeriodicTimer* class can be used.
    A *PeriodicTimer* object can call a target function periodically, as the following example
    shows.
    ```python
    from common.util import BluetoothApp, PeriodicTimer

    def periodic_task():
        print("Hello World!")

    app = BluetoothApp()
    task = PeriodicTimer(period=1, target=periodic_task)
    task.start()
    app.run()
    ```

2. You can also run the application in a separate thread, as the following example shows.
    ```python
    from threading import Thread
    from common.util import BluetoothApp

    app = BluetoothApp()
    thread = Thread(target=app.run)
    thread.start()
    print("Hello World!")
    ```
