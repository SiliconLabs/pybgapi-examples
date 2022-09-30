#!/usr/bin/env python3
"""
BtMesh NCP Light Server, OnOff Model implementation.
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

import os.path
import struct
import sys
import ctypes
import threading
import math

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from common.util import BtMeshApp
from lighting_server_gui import MainPage
from dataclasses import dataclass
from bgapi.bglib import CommandFailedError
class OnOffServer(BtMeshApp):
    def __init__(self, parser, **kwargs):
        super().__init__(parser=parser,**kwargs)
        # Current lightness level
        self.current_level = 0
        # Generic on/off state value off 
        self.on_off_state_off = 0x00
        # Generic on/off state value on
        self.on_off_state_on = 0x01
        # Copy of transition delay parameter, needed for delayed on/off request
        self.delayed_onoff_trans = 0
        # Immediate transition time is 0 seconds
        self.immediate = 0
        # Minimum brightness
        self.min_brightness = 0
        # NVM save time
        self.nvm_save_time = 5000
        # Lighting server key to store data to nvm
        self.lighting_server_key = 0x4004
        # NVM save timer
        self.lighting_nvm_save_timer = threading.Timer(self.nvm_save_time * 0.001, self.light_lightbulb_state_changed)
    @dataclass
    class lighting_lightbulb_state:
        # Current generic on/off value
        onoff_current: int = 0
        # Target generic on/off value
        onoff_target: int = 0
        # Transition time
        transtime: int = 0
        # On Power Up value
        onpowerup: int = 0
        # Current lightness value
        lightness_current: int = 0
        # Target lightness value
        lightness_target: int = 0
        # Last lightness value
        lightness_last: int = 0xFFFF
        # Default lightness value
        lightness_default: int = 0x0000
        # Minimum lightness value
        lightness_min: int = 0x0001
        # Maximum lightness value
        lightness_max: int = 0xFFFF
        # Current primary generic level value
        pri_level_current: ctypes.c_int16 = -32768
        # Target primary generic level value
        pri_level_target: ctypes.c_int16 = -32768

    def onoff_request(self, event):
        request_state = int.from_bytes(event.parameters, byteorder='little')
        self.log.info(f"ON/OFF request: requested state = {request_state}, trans = {event.transition_ms}, delay= {event.delay_ms}")

        if self.lighting_lightbulb_state.onoff_current == request_state:
            self.log.info("Request for current state received.")
        else:
            onoff_message = "ON" if request_state == 1 else "OFF"
            self.log.info(f"Turning lightbulb {onoff_message}")
            # Set target value
            self.lighting_lightbulb_state.onoff_target = request_state
            # Immediate change
            if event.transition_ms == 0 and event.delay_ms == 0:
                self.lighting_lightbulb_state.onoff_current = request_state
                
                if self.lighting_lightbulb_state.onoff_current == self.on_off_state_off:
                    self.lighting_lightbulb_state.lightness_target = 0
                    self.lighting_lightbulb_state.lightness_current = self.lighting_lightbulb_state.lightness_target
                else:
                    # Restore last brightness
                    self.lighting_lightbulb_state.lightness_target = self.lighting_lightbulb_state.lightness_last
                    self.lighting_lightbulb_state.lightness_current = self.lighting_lightbulb_state.lightness_target
                
                self.lighting_set_level(self.lighting_lightbulb_state.lightness_target, self.immediate)
            
            elif event.delay_ms > 0:
                self.delayed_onoff_trans = event.transition_ms
                # Timer start
                threading.Timer(event.delay_ms * 0.001, self.delayed_onoff_request).start()

            else:
                # No delay but transition time has been set.
                if self.lighting_lightbulb_state.onoff_target == self.on_off_state_on:
                    self.lighting_lightbulb_state.onoff_current = self.on_off_state_on
                
                self.onoff_update(event.elem_index, event.transition_ms)

                if request_state == self.on_off_state_off:
                    self.lighting_lightbulb_state.lightness_target = 0
                
                else:
                    # Restore last brightness
                    self.lighting_lightbulb_state.lightness_target = self.lighting_lightbulb_state.lightness_last

                self.lighting_set_level(self.lighting_lightbulb_state.lightness_target, event.transition_ms)
                # Lightbulb current state will be updated when transition is complete
                threading.Timer(event.transition_ms * 0.001, self.onoff_transition_complete).start()

            # Save the state in flash after a small delay
            self.lighting_nvm_save_timer_start()
            # State has changed, so the current scene number is reset
            self.lib.btmesh.scene_server.reset_register(event.elem_index)
        
        remaining_ms = event.delay_ms + event.transition_ms
        if event.flags &  2:
            # Response required. If non-zero, the client expects a response from the server.
            self.onoff_response(event.elem_index, event.client_address, event.appkey_index, remaining_ms)
        
        self.onoff_update_and_publish(event.elem_index, remaining_ms)

        # Publish to bound states
        self.lib.btmesh.generic_server.publish(
            0,
            0x1300, # MESH_LIGHTING_LIGHTNESS_SERVER_MODEL_ID
            self.lib.btmesh.generic_client.GET_STATE_TYPE_STATE_LIGHTNESS_ACTUAL
        )

    def delayed_onoff_request(self):
        """ Handle delayed light on/off requests. """
        self.log.info(f"Starting delayed ON/OFF request: {self.lighting_lightbulb_state.onoff_current} -> {self.lighting_lightbulb_state.onoff_target}, with {self.delayed_onoff_trans} ms transition")

        if self.delayed_onoff_trans == 0:
            # No transition delay, update state immediately
            self.lighting_lightbulb_state.onoff_current = self.lighting_lightbulb_state.onoff_target
            if self.lighting_lightbulb_state.onoff_current == self.on_off_state_off:
                self.lighting_set_level(self.min_brightness, self.delayed_onoff_trans)
            else:
                # Restore last brightness level
                self.lighting_set_level(self.lighting_lightbulb_state.lightness_last, self.immediate)
                self.lighting_lightbulb_state.lightness_current = self.lighting_lightbulb_state.lightness_last
                self.lighting_lightbulb_state.lightness_target = self.lighting_lightbulb_state.lightness_last

            # Save the state in flash after a small delay
            self.lighting_nvm_save_timer_start()
            self.onoff_update_and_publish(0, self.delayed_onoff_trans)

        else:
            # Delay and transition time is greather than 0
            if self.lighting_lightbulb_state.onoff_target == self.on_off_state_off:
                self.lighting_lightbulb_state.lightness_target = 0
                self.li
            else:
                self.lighting_lightbulb_state.lightness_target = self.lighting_lightbulb_state.lightness_last
                self.lighting_lightbulb_state.onoff_current = self.on_off_state_on

                self.onoff_update(0, self.delayed_onoff_trans)
            
            self.lighting_set_level(self.lighting_lightbulb_state.lightness_current, self.delayed_onoff_trans)
            # State is updated when transition is complete
            threading.Timer(self.delayed_onoff_trans * 0.001, self.onoff_transition_complete).start()

    def onoff_update(self, elem_index, remaining_ms):
        onoff = struct.pack("<BB",
            self.lighting_lightbulb_state.onoff_current,
            self.lighting_lightbulb_state.onoff_target
            )

        self.lib.btmesh.generic_server.update (
                elem_index,
                0x1000,
                remaining_ms,
                self.lib.btmesh.generic_client.GET_STATE_TYPE_STATE_ON_OFF,
                onoff
        )

    def onoff_response(self, elem_index, client_addr, appkey_index, remaining_ms):
        """ Respond to generic on/off requests. """
        self.log.info(f"Response sent")
        onoff = struct.pack("<BB",
            self.lighting_lightbulb_state.onoff_current,
            self.lighting_lightbulb_state.onoff_target
            )

        self.lib.btmesh.generic_server.respond (
            client_addr,
            elem_index, # 0
            0x1000,
            appkey_index,
            remaining_ms,
            0x00,
            self.lib.btmesh.generic_client.GET_STATE_TYPE_STATE_ON_OFF,
            onoff
        )

    def onoff_update_and_publish(self, elem_index, remaining_ms):
        self.onoff_update(elem_index, remaining_ms)

        try:
            self.lib.btmesh.generic_server.publish(
                elem_index, # 0
                0x1000,
                self.lib.btmesh.generic_client.GET_STATE_TYPE_STATE_ON_OFF
            )
        except CommandFailedError as e:
                    # Application key or publish address are not set
                    if e.errorcode != 0x514:
                        raise

    def onoff_transition_complete(self):
        """ Callback to light on/off request with non-zero transition time. """
        # Transition done -> set state, update and publish
        self.lighting_lightbulb_state.onoff_current = self.lighting_lightbulb_state.onoff_target
        onoff_message = "ON" if self.lighting_lightbulb_state.onoff_current == 1 else "OFF"
        self.log.info(f"{onoff_message}")
        # Save the state in flash after a small delay
        self.lighting_nvm_save_timer_start()
        self.onoff_update_and_publish(0, self.immediate)

    def onoff_recall(self, event):
        """ Handle generic on/off recall events. """
        request_state = int.from_bytes(event.parameters, byteorder='little')
        if self.lighting_lightbulb_state.onoff_current == self.lighting_lightbulb_state.onoff_target:
            self.log.info("Request for current OnOff state received.")
        else:
            onoff_message = "ON" if request_state == 1 else "OFF"
            self.log.info(f"Turning lightbulb {onoff_message}")

            self.lighting_lightbulb_state.onoff_target = request_state
            if event.transition_time_ms == self.immediate:
                self.lighting_lightbulb_state.onoff_current == self.lighting_lightbulb_state.onoff_target
            else:
                if self.lighting_lightbulb_state.onoff_target == self.on_off_state_on:
                    self.lighting_lightbulb_state.onoff_current = self.on_off_state_on
                
                # Lightbulb current state will be updated when transition is complete
                threading.Timer(event.transition_time_ms * 0.001, self.onoff_transition_complete).start()
            
            # Save the state in flash after a small delay
            self.lighting_nvm_save_timer_start()
        
        self.onoff_update_and_publish(event.elem_index, event.transition_time_ms)
    
    def onoff_change(self, event):
        """ Handle generic on/off change events. """
        length = len(event.parameters)
        param = event.parameters
        if length > 1:
            current = param[0]
            target = param[1]
        else:
            current = param[0]

        if current != self.lighting_lightbulb_state.onoff_current:
            self.log.info(f"On/Off state changed from {self.lighting_lightbulb_state.onoff_current} to {current}")
            self.lighting_lightbulb_state.onoff_current = current
            self.lighting_nvm_save_timer_start()
        else:
            self.log.info("On/Off change - same state as before")

    def lighting_set_level(self, level, trans_ms):
        """ Set GUI lightness level in given transition time. """
        self.current_level = level
        temp = MainPage.get_instance().temperature_value.get()
        temperature = self.temperature_to_RGB(temp)
        color = self.RGB_to_LightnessRGB(temperature, self.current_level)
        MainPage.get_instance().set_lightness_value(self.actual_value_to_precentage(self.current_level))
        MainPage.get_instance().fade(MainPage.get_instance().lightbulb_image, color, trans_ms)

    ##### HELPER FUNCTIONS #####

    def actual_value_to_precentage(self, value):
        return round((value * 100) / 0xFFFF)
    
    def temperature_to_RGB(self, temperature):
        """ Convert temperature to RGB color. """
        temp_R = 0
        temp_G = 0
        temp_B = 0

        if temperature < 6563:
            temp_R = 255
            if temperature < 1925:
                temp_B = 0
            else:
                temp_B = temperature - 1918.74282
                temp_B = 2.55822107 * pow(temp_B, 0.546877914)

            if temperature < 909:
                temp_G = 0
            else:
                temp_G = temperature - 636.62578769
                temp_G = 73.13384712 * math.log(temp_G) - 383.76244858
    
        else:
            temp_R = temperature - 5882.02392431
            temp_R = -29.28670147 * math.log(temp_R) + 450.50427359
            temp_R = temp_R + 0.5
            temp_G = temperature - 5746.13180276
            temp_G = -18.69512921 * math.log(temp_G) + 377.39334366
            temp_B = 255

        temp_max = max(temp_R, max(temp_G,temp_B))

        temp_R = temp_R * 255 / temp_max
        temp_G = temp_G * 255 / temp_max
        temp_B = temp_B * 255 / temp_max

        color_R = 255 if temp_R > 255 else (round(temp_R) if temp_R >= 0 else 0)
        color_G = 255 if temp_G > 255 else (round(temp_G) if temp_G >= 0 else 0)
        color_B = 255 if temp_B > 255 else (round(temp_B) if temp_B >= 0 else 0)

        RGB = {
            "R": color_R,
            "G": color_G,
            "B": color_B
        }

        return RGB

    def RGB_to_LightnessRGB(self, color, level):
        """ Change lightness of given color temperature. """
        new_color_R = round((color["R"] * level) / 65535)
        new_color_G = round((color["G"] * level) / 65535)
        new_color_B = round((color["B"] * level) / 65535)
    
        return "#" + f"{new_color_R:02X}" + f"{new_color_G:02X}" + f"{new_color_B:02X}"

    def light_lightbulb_state_changed(self):
        """ Save the state to the nvm after the lighting lightbulb state is changed. """
        self.lib.bt.nvm.save(
            self.lighting_server_key,
            self.lightbulb_state_serialize()
        )
    
    def lighting_nvm_save_timer_start(self):
        """ Start or restart lighting NVM save timer. """
        if self.lighting_nvm_save_timer.is_alive():
            self.lighting_nvm_save_timer.cancel()
        self.lighting_nvm_save_timer = threading.Timer(self.nvm_save_time * 0.001, self.light_lightbulb_state_changed)
        self.lighting_nvm_save_timer.start()
    
    def lightbulb_state_serialize(self):
        """ Pack dataclass to a struct for NVM save. """
        lightbulb_state= struct.pack("<BBBBHHHHHHhh",
            self.lighting_lightbulb_state.onoff_current,
            self.lighting_lightbulb_state.onoff_target,
            self.lighting_lightbulb_state.transtime,
            self.lighting_lightbulb_state.onpowerup,
            self.lighting_lightbulb_state.lightness_current,
            self.lighting_lightbulb_state.lightness_target,
            self.lighting_lightbulb_state.lightness_last,
            self.lighting_lightbulb_state.lightness_default,
            self.lighting_lightbulb_state.lightness_min,
            self.lighting_lightbulb_state.lightness_max,
            self.lighting_lightbulb_state.pri_level_current,
            self.lighting_lightbulb_state.pri_level_target
        )
        return lightbulb_state
    