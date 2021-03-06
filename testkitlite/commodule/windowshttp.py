#!/usr/bin/python
#
# Copyright (C) 2012 Intel Corporation
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Authors:
#           Tang, Shaofeng <shaofeng.tang@intel.com>

""" The implementation of Windows HTTP communication"""

import os
import time
import socket
import threading
import re
import sys
from shutil import copyfile
from testkitlite.util.log import LOGGER
from testkitlite.util.autoexec import shell_command, shell_command_ext
from testkitlite.util.killall import killall
from testkitlite.util.httprequest import get_url, http_request
from testkitlite.util.errors import InvalidDeviceException


HOST_NS = "127.0.0.1"
os.environ['no_proxy'] = HOST_NS
os.environ['TEST_PLATFORM'] = 'windows'
os.environ['CONNECT_TYPE'] = 'http'


WIN_MAIN = "xwalk.exe"
#C:\Program Files\webapi-promises-nonw3c-tests\xwalk.exe C:\Program Files\webapi-promises-nonw3c-tests\webapi-promises-nonw3c-tests/manifest.json
LAUNCH_XWALK = "\"c:\\Program Files\\%s\\xwalk.exe\" \"c:\\Program Files\\%s\\%s\\manifest.json\""
LAUNCH_XWALK_EXTENSIONS = "\"c:\\Program Files\\%s\\xwalk.exe\" \"c:\\Program Files\\%s\\%s\\manifest.json\" \"--use-rs-video-capture\" --external-extensions-path=\"c:\\Program Files\\%s\\%s\""
QUERY_XWALK = "tasklist | findstr xwalk.exe"
KILL_XWALK = "taskkill /im xwalk.exe /f"


class windowsHttp:
    
    """ Implementation for transfer data
        between Host and IVI/PC on SSH connection
    """

    def __init__(self, deviceip):
        self.deviceip = deviceip


######### commodule initialization begin #############
    def get_device_info(self):
        """
            get windows deivce inforamtion
        """
        device_info = {}
        resolution_str = ""
        screen_size_str = ""
        device_model_str = ""
        device_name_str = ""
        build_id_str = ""
        os_version_str = ""

        device_info["device_id"] = self.deviceip
        device_info["resolution"] = resolution_str
        device_info["screen_size"] = screen_size_str
        device_info["device_model"] = device_model_str
        device_info["device_name"] = device_name_str
        device_info["os_version"] = os_version_str
        device_info["build_id"] = build_id_str
        
        return device_info

    # Get device build info
    def get_buildinfo(self):
        """ get builf info"""
        build_info = {}
        build_info['buildid'] = ''
        build_info['manufacturer'] = ''
        build_info['model'] = ''
        return build_info

    # 
    def get_launcher_opt(self, test_launcher, test_ext, test_widget, test_suite, test_set):
        """
        get test option dict
        """
        test_opt = {}
        test_opt["launcher"] = WIN_MAIN
        LOGGER.info("[ test_ext: %s; test_widget: %s; test_suite: %s]" % (test_ext, test_widget, test_suite))
        test_opt["test_app_id"] = test_suite

        return test_opt


    # The stub is launched by stub-demon 9000 on Windows 
    # curl http://deviceIp:9000/check_stub
    def check_process(self, process_name):
        stub_status = 0       
        server_url = "http://%s:9000" % self.deviceip
        LOGGER.error("[ Server URL: %s]" % server_url)
        ret = http_request(
            get_url(server_url, "/check_stub"), "GET", {})
        if ret is None:
            LOGGER.error("[ ERROR: get server status timeout, please check deivce! ]")
        else: 
            if ret.get("OK") is not None:
                stub_status = 1
        return stub_status

    # The stub is launched by stub-demon 9000 on Windows 
    # curl http://deviceIp:9000/launch_stub
    def launch_stub(self, stub_app, stub_port="8000", debug_opt=""):
        stub_status = False
        server_url = "http://%s:9000" % self.deviceip
        ret = http_request(
            get_url(server_url, "/launch_stub"), "GET", {})
        if ret is None:
            LOGGER.error("[ ERROR: get server status timeout, please check deivce! ]")
        else: 
            if ret.get("OK") is not None:
                stub_status = True
        return stub_status

    # The stub is launched by stub-demon 9000 on Windows 
    # curl http://deviceIp:9000/kill_stub
    def kill_stub(self):
        stub_status = False
        server_url = "http://%s:9000" % self.deviceip
        ret = http_request(
            get_url(server_url, "/kill_stub"), "GET", {})
        if ret is None:
            LOGGER.error("[ ERROR: get server status timeout, please check deivce! ]")
        else: 
            if ret.get("OK") is not None:
                stub_status = True
        return stub_status

    def get_server_url(self, remote_port="8000"):
        """get server url"""
        remote_ip = self.deviceip
        os.environ['no_proxy'] = remote_ip
        url_forward = "http://%s:%s" % (remote_ip, remote_port)
        return url_forward

######### commodule initialization end #############

######### commodule TC execution begin #############
    def start_debug(self, dlogfile):
        global debug_flag, metux
        debug_flag = True

    def launch_app(self, wgt_name, extension=None):
        blauched = False
        cmdline = LAUNCH_XWALK % (wgt_name, wgt_name, wgt_name)
        if extension is not None:
            cmdline = LAUNCH_XWALK_EXTENSIONS % (wgt_name, wgt_name, wgt_name, wgt_name, extension)
        cmd_json = {}
        cmd_json['cmd'] = cmdline
        server_url = "http://%s:8000" % self.deviceip
        ret = http_request(
            get_url(server_url, "/execute_async_cmd"), "POST", cmd_json, 30)
        time.sleep(3)

        cmdline = QUERY_XWALK
        cmd_json['cmd'] = cmdline
        ret = http_request(
            get_url(server_url, "/execute_cmd"), "POST", cmd_json, 30)
        if ret and len(ret):
            blauched = True
        LOGGER.info("[ Launch test cases launcher: %s" % blauched);
        return blauched

    def kill_app(self, wgt_name):
        cmd_json = {}
        cmd_json['cmd'] = KILL_XWALK
        server_url = "http://%s:8000" % self.deviceip
        ret = http_request(
            get_url(server_url, "/execute_async_cmd"), "POST", cmd_json, 30)
        time.sleep(3)
        return True

    def stop_debug(self):
        global debug_flag
        debug_flag = False

    def shell_cmd_ext(self,
                      cmd="",
                      timeout=None,
                      boutput=False,
                      stdout_file=None,
                      stderr_file=None):
        check_stub_num = 0
        while (not self.check_process("")) and check_stub_num < 3:
            self.launch_stub("")
            check_stub_num += 1
            time.sleep(3)
        cmd_json = {}
        cmd_json['cmd'] = cmd
        server_url = "http://%s:8000" % self.deviceip
        result = http_request(
            get_url(server_url, "/general_cmd_response"), "POST", cmd_json, 30)
        if result is not None:
            LOGGER.info("Response exit_code: %s" % result["exit_code"])
            LOGGER.info("Response output: %s" % result["output"])
            time.sleep(1)
            return [int(result["exit_code"]), result["output"], []]
        else:
            LOGGER.info("Fail to connect stub!")
            return [-1, ["Fail to connect stub"], []]

######### commodule TC execution end #############

def get_target_conn(deviceip=None):
    """ Get connection for Test Target"""
    if deviceip is None:
        raise InvalidDeviceException('deviceid("IP address") is required by http connection!')
    return windowsHttp(deviceip)


