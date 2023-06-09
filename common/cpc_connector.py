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

import sys
import threading
from bgapi.connector import Connector, ConnectorException
try:
    import libcpc
except ModuleNotFoundError:
    # Suppress exception until CPC connector is not used
    pass

class SerialConnectorCPC(Connector):
    """ CPC serial connector """
    def __init__(self, lib_path, cpc_instance=None, tracing=False, endpoint_id=None):
        if "libcpc" not in sys.modules:
            raise ModuleNotFoundError("No module named 'libcpc'")
        self.endpoint = None
        self.endpoint_id = endpoint_id
        if self.endpoint_id is None:
            self.endpoint_id = libcpc.Endpoint.Id.BLUETOOTH.value
        self.read_timeout = None
        self.write_timeout = None
        self.reset_event = threading.Event()
        try:
            self.cpc = libcpc.CPC(lib_path, cpc_instance, tracing, self.reset_event.set)
        except Exception as err:
            raise ConnectorException(err) from err
        self.read_buff = bytearray()

    def open(self):
        """ Opening CPC endpoint """
        try:
            self.endpoint = self.cpc.open_endpoint(self.endpoint_id)
            # Send handshake message (system hello)
            self.endpoint.write(b"\x20\x00\x01\x00")
        except Exception as err:
            raise ConnectorException(err) from err

    def close(self):
        """ Closing CPC endpoint """
        if self.endpoint is not None:
            del self.read_buff[:]
            try:
                self.endpoint.close()
            except Exception as err:
                raise ConnectorException(err) from err

    def write(self, data):
        """ Write data to the endpoint """
        try:
            self._check_reset()
            self.endpoint.write(data)
        except Exception as err:
            raise ConnectorException(err) from err

    def read(self, size=1):
        """ Read size number of data from endpoint """
        if len(self.read_buff) < size:
            try:
                self._check_reset()
                data = self.endpoint.read()
                self.read_buff.extend(data)
            except Exception:
                # Read timeout, return with empty data
                return bytearray(0)

        ret = self.read_buff[0:size]
        del self.read_buff[0:size]

        return ret

    def set_read_timeout(self, timeout):
        """ Set read timeout """
        self.read_timeout = timeout
        time = libcpc.CPCTimeval(timeout)
        self.endpoint.set_option(libcpc.Option.CPC_OPTION_RX_TIMEOUT, time)

    def set_write_timeout(self, timeout):
        """ Set write timeout """
        self.write_timeout = timeout
        time = libcpc.CPCTimeval(timeout)
        self.endpoint.set_option(libcpc.Option.CPC_OPTION_TX_TIMEOUT, time)

    def _check_reset(self):
        """ Check reset event and perform reset """
        if self.reset_event.is_set():
            self.reset_event.clear()
            self.close()
            self.cpc.restart()
            self.open()
            if self.read_timeout is not None:
                self.set_read_timeout(self.read_timeout)
            if self.write_timeout is not None:
                self.set_read_timeout(self.write_timeout)
