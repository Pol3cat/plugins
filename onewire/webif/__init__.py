#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2020-     <AUTHOR>                                   <EMAIL>
#########################################################################
#  This file is part of SmartHomeNG.
#  https://www.smarthomeNG.de
#  https://knx-user-forum.de/forum/supportforen/smarthome-py
#
#  Sample plugin for new plugins to run with SmartHomeNG version 1.5 and
#  upwards.
#
#  SmartHomeNG is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHomeNG is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHomeNG. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import datetime
import time
import os
import json

from lib.item import Items
from lib.model.smartplugin import SmartPluginWebIf


# ------------------------------------------
#    Webinterface of the plugin
# ------------------------------------------

import cherrypy
import csv
from jinja2 import Environment, FileSystemLoader



class WebInterface(SmartPluginWebIf):

    def __init__(self, webif_dir, plugin):
        """
        Initialization of instance of class WebInterface

        :param webif_dir: directory where the webinterface of the plugin resides
        :param plugin: instance of the plugin
        :type webif_dir: str
        :type plugin: object
        """
        self.logger = plugin.logger
        self.webif_dir = webif_dir
        self.plugin = plugin
        self.tplenv = self.init_template_environment()

        self.items = Items.get_instance()

    @cherrypy.expose
    def index(self, reload=None):
        """
        Build index.html for cherrypy

        Render the template and return the html file to be delivered to the browser

        :return: contents of the template after beeing rendered
        """
        global_pagelength = cherrypy.config.get("webif_pagelength")
        if global_pagelength:
            pagelength = global_pagelength
            self.logger.debug("Global pagelength {}".format(pagelength))
        else:
            pagelength = 100
            self.logger.debug("Default pagelength {}".format(pagelength))
        # try to get the webif pagelength from the plugin specific plugin.yaml configuration
        try:
            pagelength = self.plugin.webif_pagelength
            self.logger.debug("Plugin pagelength {}".format(pagelength))
        except Exception:
            pass
        tmpl = self.tplenv.get_template('index.html')
        # add values to be passed to the Jinja2 template eg: tmpl.render(p=self.plugin, interface=interface, ...)
        return tmpl.render(p=self.plugin,
                           webif_pagelength=pagelength,
                           items=sorted(self.items.return_items(), key=lambda k: str.lower(k['_path'])))


    @cherrypy.expose
    def get_data_html(self, dataSet=None):
        """
        Return data to update the webpage

        For the standard update mechanism of the web interface, the dataSet to return the data for is None

        :param dataSet: Dataset for which the data should be returned (standard: None)
        :return: dict with the data needed to update the web page.
        """
        if dataSet is None:
            result_array = []

            # callect data for 'items' tab
            item_list = []
            for item in self.plugin.get_item_list():
                item_config = self.plugin.get_item_config(item)
                value_dict = {}
                value_dict['path'] = item.id()
                value_dict['type'] = item.type()
                value_dict['not_discovered'] = (item_config['bus'] == '')
                value_dict['sensor_addr'] = item_config['sensor_addr']
                value_dict['deviceclass'] = item_config['deviceclass']
                value_dict['value'] = item()
                value_dict['value_unit'] = item_config['unit']
                value_dict['last_update'] = item.property.last_update.strftime('%d.%m.%Y %H:%M:%S')
                value_dict['last_change'] = item.property.last_change.strftime('%d.%m.%Y %H:%M:%S')
                item_list.append(value_dict)

            # callect data for 'buses' tab
            bus_dict = {}
            device_list = []
            for bus in self.plugin._buses:
                if bus_dict.get(bus, None) is None:
                    bus_dict[bus] = 0

                for device in self.plugin._webif_buses[bus]:
                    bus_dict[bus] += 1
                    value_dict = {}
                    value_dict['device'] = device
                    value_dict['bus'] = bus
                    value_dict['deviceclass'] = self.plugin._webif_buses[bus][device]['deviceclass']
                    value_dict['devicetype'] = self.plugin._webif_buses[bus][device]['devicetype']
                    value_dict['items_defined'] = self.plugin.count_items_for_device(device)
                    value_dict['keys'] = self.plugin._webif_buses[bus][device]['keys']
                    device_list.append(value_dict)

            bus_list = []
            for bus in bus_dict:
                value_dict = {}
                value_dict['bus'] = bus
                value_dict['devicecount'] = bus_dict[bus]
                bus_list.append(value_dict)

            bus_list = sorted(bus_list, key=lambda d: d['bus'])
            result = {'items': item_list, 'buses': bus_list, 'devices': device_list}

            # send result to wen interface
            try:
                data = json.dumps(result)
                if data:
                    return data
                else:
                    return None
            except Exception as e:
                self.logger.error(f"get_data_html exception: {e}")

        return {}