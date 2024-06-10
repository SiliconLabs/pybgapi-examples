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
    python3 example/bt_empty/app.py
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

On Linux systems, an additional CPC layer is available that provides additional security and
robustness. For further details, see [Co-Processor Communication](https://docs.silabs.com/gecko-platform/latest/service/cpc/overview).

[AN1259: Using the v3.x Silicon Labs Bluetooth® Stack in Network CoProcessor Mode](https://www.silabs.com/documents/public/application-notes/an1259-bt-ncp-mode-sdk-v3x.pdf)
provides a detailed description how NCP works and how to configure it for CPC and custom hardware.

For the latest BGAPI documentation, see [docs.silabs.com](https://docs.silabs.com/bluetooth/latest/).

## Generic Application Classes

All example applications in this repo are based on the generic application classes. These classes
are defined in [util.py](common/util.py) and provide all the common code that the example
applications share. Therefore, the user code contains only the bare minimum without duplication.
It also makes writing a custom event-driven application quite simple. The application classes have
a multi-level inheritance chain, where each inheritance level adds extra features and becomes more
specialized.

### GenericApp

This class provides the skeleton for all application classes. It is responsible for connecting to an
NCP Target and receiving the events in an infinite loop.

Its constructor instantiates one `BGLib` object, which is accessible in its `lib` attribute. This
`lib` object is the interface for sending BGAPI commands to the target.

The execution of the application starts by calling the `run` method. This method opens the
connection (e.g., the serial port of a WSTK board), performs a reset to get to a well-defined
state, and receives events from the NCP Target in an infinite loop. The event reception happens
in a blocking manner without timeout. It also implies that the `run` method is a synchronous call,
i.e., the execution of the script will continue when the running terminates. If the running
terminates for one of the following reason, the connection will be closed and the script execution
continues:
- User interruption with the `Ctrl` + `C` keys.
- Programmatically calling the `stop` method.
- Upon BGAPI command failure.

The execution can be started in an asynchronous mode too by calling the `start` method. It starts
the `run` method in its own thread and returns immediately. The main thread will terminate once all
the non-daemon threads are terminated. Please note that in this case the `KeyboardInterrupt` has to
be handled in the main thread. See the [Troubleshooting](#troubleshooting) chapter for details.

### BluetoothApp

This class extends the *GenericApp* with the following features.

#### Check BGAPI Version

Every Bluetooth SDK comes with an XAPI file that describes the actual version of the BGAPI protocol.
This repo contains a copy of the XAPI file. The examples are written based on this copy. The BGAPI
versions on the host and target side should be aligned. Otherwise, unexpected issues may happen.
On a boot event, the version of the XAPI file and the Bluetooth stack version running on the NCP
Target are compared and a warning message is printed if they do not match.

#### Print Bluetooth Address

On a boot event, the Bluetooth address is read from the NCP Target and printed on the console.
The address is also cached in the `address` and `address_type` attributes, so it can be accessed
later without NCP communication overhead.

#### Implement Soft Reset

The *BluetoothApp* overrides the empty `reset` method of the *GenericApp* that is called by the
`run` method. When called, the device will restart in normal boot mode.

#### Default XAPI File

The *BluetoothApp* uses the [sl_bt.xapi](api/sl_bt.xapi) file by default in its constructor.

### BtMeshApp

This class extends the *GenericApp* with the following features.

#### Check BGAPI Version

Every Bluetooth SDK comes with an XAPI file that describes the actual version of the BGAPI protocol.
This repo contains a copy of the XAPI file. The examples are written based on this copy. The BGAPI
versions on the host and target side should be aligned. Otherwise, unexpected issues may happen.
On a boot event, the version of the XAPI file and the Bluetooth stack version running on the NCP
Target are compared and a warning message is printed if they do not match.

#### Initialize Mesh Node

Initializes the Bluetooth mesh stack in Node role. When initialization is complete, a node initialized
event will be generated. This command must be issued before any other Bluetooth mesh commands.
Note that you may initialize a device either in the Provisioner or the Node role, but not both.

#### Implement Soft and Node Reset

The *BtMeshApp* overrides the empty `reset` method of the *GenericApp* that is called by the
`run` method. When called, the device will restart in normal boot mode without any previous node
configuration parameters. In other words, if the node was previously provisioned into a network,
it will be removed.

#### Default XAPI File

The *BtMeshApp* uses both the Bluetooth [sl_bt.xapi](api/sl_bt.xapi) and Bluetooth mesh
[sl_btmesh.xapi](api/sl_btmesh.xapi) XAPI files by default in its constructor.

## Argument Parser

The `ArgumentParser` class is derived from the standard `argparse.ArgumentParser` class. This class
has default arguments optimized for the generic application classes to set up connection parameters
and the logging level. In combination with the `get_connector` method, it's supposed to set up the
host-to-target connection effortlessly. It supports single connection (default) and multi connection
mode too. Invoke the example scripts with the `-h` switch to get more details about the available
options. Custom arguments can be added as documented in the standard `argparse.ArgumentParser` class.

## Examples

Most of the examples in this repo reproduce the behavior of existing C examples from the GSDK.
The examples can be tested together with the [EFR Connect](https://www.silabs.com/developers/efr-connect-mobile-app)
mobile app.
See the documentation of the original C examples to get more information.

- [Bluetooth - Empty](example/bt_empty)
- [Bluetooth - iBeacon](example/bt_ibeacon)
- [Bluetooth - NCP test](example/bt_ncp_test)
- [Bluetooth - Roaming](example/bt_roaming)
- [Bluetooth - Thermometer](example/bt_thermometer)
- [Bluetooth - Thermometer Client](example/bt_thermometer_client)
- [Bluetooth mesh - Empty](example/btmesh_empty)

## Creating a Custom Application

To create a custom Bluetooth application, follow these steps:
- Import the [util.py](common/util.py) module.
- Get a connector instance using the `get_connector` function.
- Create your own application class inherited from the `BluetoothApp` class.
- Add Bluetooth event handler methods, named after the event to be handled.
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

Also note that the pyBGAPI is more sensitive to the API deprecations because, unlike the C
implementation of the BGAPI, it has no compatibility layer.

#### Solution

1. Update the Bluetooth SDK in Simplicity Studio and Flash the **Bluetooth - NCP** demo example
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
  File 'example/bt_empty/app.py', line 65, in gattdb_init
    _, session = self.lib.bt.gattdb.new_session()
```

#### Explanation

The error code `0xf` means that the feature is not supported and refers to the Bluetooth dynamic
GATT database feature. Most likely, the root case is that the *Bluetooth - NCP Empty* example has
been flashed on the target instead of the *Bluetooth - NCP*. The difference is that the *NCP Empty*
example contains an ***almost*** empty static GATT database, while the *NCP* contains no static
GATT database at all, but the dynamic GATT database feature instead. The dynamic GATT database
feature makes it possible to configure the GATT database entirely from the host side. The
examples in this repo utilize this feature.

#### Solution

Flash the **Bluetooth - NCP** example on your development board.

### app.run() Blocks the Script from Executing

#### Observed Behavior

Code after `app.run()` call executes only after the app terminates.

#### Explanation

The *GenericApp* class can be executed both in synchronous (blocking) mode and asynchronous
(non-blocking) mode. Most examples use the synchronous mode per default.

#### Solution

Use the `start` method of the app instead of the `run` method. See the following example for a
minimal working code.

```python
import time
from common.util import BluetoothApp, get_device_list
app = BluetoothApp(get_device_list()[0])
app.start()
# Place your custom code here
print("Hello World!")
# Catch KeyboardInterrupt
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    app.stop()
```
