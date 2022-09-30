"""
BtMesh NCP Light Server GUI.
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

import tkinter
import colour
import os.path
import logging
from PIL import ImageTk,Image

class windows(tkinter.Tk):
    """ Root window for the frame. """
    def __init__(self, app, *args, **kwargs):
        tkinter.Tk.__init__(self, *args, **kwargs)
        self.protocol("WM_DELETE_WINDOW", app.stop)
        self.resizable(0,0)

        # Adding a title to the window
        self.wm_title("BT Mesh Light")

        # Creating a frame and assigning it to container
        container = tkinter.Frame(self, height=400, width=600)

        # Specifying the region where the frame is grided
        container.grid(column=0, row=0)
        self.geometry("300x160")
 
        # Configuring the location of the container using grid
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        frame = MainPage(self, app)
        frame.grid(row=0, column=0, sticky="nsew")
   
class MainPage(tkinter.Frame):
    """ Implementation of the used frame. """
    __instance = None
    @staticmethod
    def get_instance(self):
        if MainPage.__instance == None:
            self.gui_log.info("No instance for GUI yet")
        return MainPage.__instance

    def __init__(self, parent, app):
        self.gui_log = logging.getLogger(str(type(self)))
        tkinter.Frame.__init__(self, parent)
        if MainPage.__instance != None:
            self.gui_log.error("GUI instance is already present")
            return
        self.root = self
        self.app = app
        MainPage.__instance = self
        
        # Variables
        self.lightness_value = tkinter.IntVar()
        self.temperature_value = tkinter.IntVar()
        self.temperature_value.set(6500)
        self.delta_uv_value = tkinter.DoubleVar()
        # Image size
        self.pixels_x = 100
        self.pixels_y = 100

        # Lightness
        slider_label = tkinter.Label(
            self,
            text='Lightness:'
        )

        slider_label.grid(
            row=1,
            column=2,
            sticky=tkinter.S
        )

        self.lightness_value_label = tkinter.Label(
            self,
            text=f"{self.lightness_value.get()}%"
        )

        self.lightness_value_label.grid(
            row=1,
            column=3,
            sticky=tkinter.SE,
            padx=5,
            pady=5
        )

        # Temperature
        slider_label = tkinter.Label(
            self,
            text='Temperature:'
        )

        slider_label.grid(
            column=2,
            row=2,
            sticky=tkinter.S
        )

        self.temperature_value_label = tkinter.Label(
            self,
            text=f"{self.temperature_value.get()}K"
        )

        self.temperature_value_label.grid(
            row=2,
            column=3,
            sticky=tkinter.SE,
            padx=5,
            pady=5
        )

        # Delta UV
        slider_label = tkinter.Label(
            self,
            text='Delta UV:'
        )

        slider_label.grid(
            column=2,
            row=3,
            sticky=tkinter.S
        )

        self.delta_uv_value_label = tkinter.Label(
            self,
            text=f"{self.delta_uv_value.get():.2f}"
        )
        self.delta_uv_value_label.grid(
            row=3,
            column=3,
            sticky=tkinter.SE,
            padx=5,
            pady=5
        )

        # Factory reset button
        factory_reset = tkinter.Button(
            self,
            text="Factory reset",
            command=self.factory_reset
        )

        factory_reset.grid(
            row=4,
            column=3,
            sticky=tkinter.SE,
            padx=5,
            pady=5
        )

        # Node reset button
        node_reset = tkinter.Button(
            self,
            text="Node reset",
            command=self.node_reset
        )

        node_reset.grid(
            row=4,
            column=1,
            sticky=tkinter.SW,
            padx=5,
            pady=5
        )

        ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
        image_path = Image.open(os.path.join(ROOT_DIR, 'btmesh_light\images', 'lightbulb.png'))
        self.load_image = ImageTk.PhotoImage(image_path.resize((self.pixels_x, self.pixels_y)))
        self.lightbulb_image = tkinter.Label(self, image=self.load_image, borderwidth=4, bg="black")

        self.lightbulb_image.grid(
            row=1,
            column=0,
            rowspan=3,
            columnspan=2,
            padx=5,
            pady=5)

    __instance = None
    @staticmethod
    def get_instance():
        if MainPage.__instance == None:
            self.gui_log.info("no instance yet")
        return MainPage.__instance

    def set_lightness_value(self, value):
        """ Set the Lightness value and updates the GUI. """
        self.lightness_value.set(value)
        self.lightness_value_label.configure(text=f"{self.lightness_value.get()}%")

    def set_temperature_value(self, value):
        """ Set the Temperature value and updates the GUI. """
        self.temperature_value.set(value)
        self.temperature_value_label.configure(text=f"{self.temperature_value.get()}K")

    def set_delta_uv_value(self, value):
        """ Set the Delta UV value and updates the GUI. """
        self.delta_uv_value.set(value)
        self.delta_uv_value_label.configure(text=f"{self.delta_uv_value.get():.2f}")
    
    def factory_reset(self):
        """ Call the factory reset function from the General class. """
        self.set_lightness_value(0)
        self.set_temperature_value(6500)
        self.set_delta_uv_value(0)
        self.fade(self.lightbulb_image, "#000000", 0)
        self.app.factory_reset()

    def node_reset(self):
        """ Call the node reset function from the General class. """
        self.set_lightness_value(0)
        self.set_temperature_value(6500)
        self.set_delta_uv_value(0)
        self.fade(self.lightbulb_image, "#000000", 0)
        self.app.node_reset()

    def fade(self, widget, bg, trans_ms):
        """
        Show faded effect on widget's different color options.

        :param widget: image with no background
        :param bg: fade background color to the given color (str)
        :param trans_ms: transition time in ms
        """
        if trans_ms == 0:
            widget.config(bg = bg)
        else:
            if not getattr(widget, '_after_ids', None): widget._after_ids = {}
            widget.after_cancel(widget._after_ids.get("bg", ' '))
            c1 = tuple(map(lambda a: a/(65535), widget.winfo_rgb(widget["bg"])))
            c2 = tuple(map(lambda a: a/(65535), widget.winfo_rgb(bg)))

            colors = tuple(colour.rgb2hex(c, force_long=True)
            for c in colour.color_scale(c1, c2, max(1, int((trans_ms*60)//1000))))

            def worker(count=0):
                if len(colors)-1 <= count:
                    return
                widget.config({"bg" : colors[count]})
                widget._after_ids.update( { "bg": widget.after(
                    1000//60, worker, count+1) } )

            worker()

    def lighting_server_gui_thread(app):
        gui=windows(app=app)
        gui.mainloop()
