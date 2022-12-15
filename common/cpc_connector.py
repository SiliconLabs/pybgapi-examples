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

from bgapi.connector import Connector, ConnectorException
from . import libcpc_wrapper as lcw

class SerialConnectorCPC(Connector):
    """ CPC serial connector """
    def __init__(self, lib_path, cpc_instance, tracing=False, endpoint_id=None):
        """ Init """
        self.endpoint = None
        self.lib_path = lib_path
        self.cpc_instance = cpc_instance
        try:
            self.cpc = lcw.CPC(self.lib_path, self.cpc_instance, tracing, self.cpc_reset)
        except Exception as err:
            raise ConnectorException(err) from err
        self.read_buff = bytearray()
        if endpoint_id is not None:
            self.endpoint_id = endpoint_id
        else:
            self.endpoint_id = lcw.Endpoint.Id.BLUETOOTH.value # Bluetooth (BGAPI) endpoint
        # Only a window of 1 is supported at the moment, see CPC library documentation
        self.tx_window_size = 1

    def open(self):
        """ Opening CPC endpoint """
        try:
            self.endpoint = self.cpc.open_endpoint(self.endpoint_id, self.tx_window_size)
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
            self.endpoint.write(data)
        except Exception as err:
            raise ConnectorException(err) from err

    def read(self, size=1):
        """ Read size number of data from endpoint """
        if len(self.read_buff) < size:
            try:
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
        time = lcw.CPCTimeval(timeout)
        self.endpoint.set_option(lcw.Option.CPC_OPTION_RX_TIMEOUT, time)

    def set_write_timeout(self, timeout):
        """ Set write timeout """
        time = lcw.CPCTimeval(timeout)
        self.endpoint.set_option(lcw.Option.CPC_OPTION_TX_TIMEOUT, time)

    def cpc_reset(self):
        """ Restart the CPC library """
        self.cpc.restart()
        del self.read_buff[:]
        try:
            self.endpoint = self.cpc.open_endpoint(self.endpoint_id, self.tx_window_size)
        except Exception as err:
            raise ConnectorException(err) from err
