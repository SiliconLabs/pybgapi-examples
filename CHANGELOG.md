# Changelog

The releases in this repo are based on particular [GSDK releases](https://github.com/SiliconLabs/gecko_sdk/releases).
The version numbers here reflect the GSDK version that the release is based on.

## [4.3.0] - 2023-06-09

### Fixed
- Various issues with CPC reset

### Changed
- Update BGAPI version to 6.0.0.

### Removed
- libcpc_wrapper.py. Install libcpc module from the [cpc-daemon](https://github.com/SiliconLabs/cpc-daemon) repo.

## [4.2.0] - 2022-12-15

### Added
- bt_roaming example

### Changed
- Update BGAPI version to 5.0.0.
- `GenericApp` class derived from `threading.Thread`, therefore it's easier to
  start `GenericApp` instances in their own thread.
- Events can be handled in their dedicated event callback methods in addition to
  the generic `event_handler` method of the `GenericApp`.
- `ConnectorApp` class removed, its functionality moved to `ArgumentParser` class
  and`get_connector` functions.
- `BluetoothApp` and `BtmeshApp` classes derived directly from `GenericApp`,
  they need a connector instance in their constructor.
- `PeriodicTimer` replaced with threading objects in `bt_thermometer` example.
- Timestamp added to logging messages.
- Libcpc_wrapper script updated.

### Removed
- `PeriodicTimer` helper class

## [4.1.2] - 2022-09-30
### Added
- btmesh_light and btmesh_switch examples.
- CPC support (Linux only).
- 'bt_' prefix for BLE example names.
- Readme files in the example folders.
- This change log.

### Changed
- Update BGAPI version to 4.2.0.

### Fixed
- Float conversion issue with bt_thermometer_client example.

## [4.0.0] - 2021-12-20
### Changed
- Update BGAPI version to 3.3.0.
- Node reset removed from Bluetooth mesh reset.

## 3.2.2 - 2021-09-14
### Added
- Initial public release.

[4.3.0]: https://github.com/SiliconLabs/gecko_sdk/releases/tag/v4.3.0
[4.2.0]: https://github.com/SiliconLabs/gecko_sdk/releases/tag/v4.2.0
[4.1.2]: https://github.com/SiliconLabs/gecko_sdk/releases/tag/v4.1.2
[4.0.0]: https://github.com/SiliconLabs/gecko_sdk/releases/tag/v4.0.0
