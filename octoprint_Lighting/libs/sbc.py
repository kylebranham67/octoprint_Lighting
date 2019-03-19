'''
This module contain factory patter for different hardware platforms. Adding new platform is simple, first you need
add class with inheriting from SBC. Inside you have to define differences between parent class and child. You can easily
overwrite methods and parameters. For reference please look at Armbiand and RPi classes.
Last step is to define way of detecting platform type. It could be very different depending on OS.
'''

import os
import re


class SBCFactory(object):

    piSocTypes = (["BCM2708", "BCM2709",
                        "BCM2835"])  # Array of raspberry pi SoC's to check against, saves having a large if/then statement later

    # Create based on class name:
    def factory(self, logger):
        """
        Method is returning handler to object based on defined criteria
        :param logger: global logger
        :return: handler to proper object
        """
        if self._is_armbian():
            return Armbian(logger)
        elif self._is_rpi(logger):
            return RPi(logger)

        return SBC()

    def _is_rpi(self, logger):
        """
        Detecting if is RPi - based on original code
        :param logger:
        :return:
        """
        with open('/proc/cpuinfo', 'r') as infile:
            cpuinfo = infile.read()
        # Match a line like 'Hardware   : BCM2709'
        match = re.search('Hardware\s+:\s+(\w+)', cpuinfo, flags=re.MULTILINE | re.IGNORECASE)

        if not match:
            return False
        elif match.group(1) in self.piSocTypes:
            logger.info("Broadcom detected")
            return True
        return False

    def _is_armbian(self):
        """
        Detecting armbian - checking if armbian monitor exist
        :return:
        """
        return os.path.exists("/etc/armbianmonitor")


class SBC(object):

    temp_cmd = ''
    is_supported = False
    debugMode = False
    parse_pattern = ''

    def checkSoCTemp(self):
        if self.is_supported:
            from sarge import run, Capture

            self._logger.info("Checking SoC internal temperature")
            p = run(self.temp_cmd, stdout=Capture())
            if p.returncode == 1:
                self.is_supported = False
                self._logger.info("SoC temperature not found.")
            else:
                p = p.stdout.text

            # elif self.debugMode:  # doesn't work on linux
            #     import random
            #     def randrange_float(start, stop, step):
            #         return random.randint(0, int((stop - start) / step)) * step + start
            #
            #     p = "temp=%s'C" % randrange_float(5, 60, 0.1)

            self._logger.debug("response from sarge: %s" % p)
            self._logger.debug("used pattern: %r" % self.parse_pattern)
            match = re.search(self.parse_pattern, p)
            temp = 0
            if not match:
                self._logger.debug("match: not found")
                self.is_supported = False
            else:
                temp = self.parse_tepmerature(match)
                self._logger.debug("match: %s" % str(temp))

            return temp
        return 0

    def parse_tepmerature(self, re_output):
        return re_output.group(1)


class RPi(SBC):

    def __init__(self, logger):
        self.is_supported = True
        self.temp_cmd = '/opt/vc/bin/vcgencmd measure_temp'
        self.parse_pattern = '=(.*)\''
        self._logger = logger


class Armbian(SBC):

    def __init__(self, logger):
        self.is_supported = True
        self.temp_cmd = 'cat /etc/armbianmonitor/datasources/soctemp'
        self.parse_pattern = '(\d+)'
        self._logger = logger

    def parse_tepmerature(self, re_output):
        """
        We are expecting that temp of SoC will be no more that 3 digit int. Armbian on Odroid is returning ex 44000 but
        on orangePi 26
        :param re_output:
        :return:
        """
        # TODO: depending on situation in the future maybe it will be necessary to split it.
        temp = re_output.group(1)
        if len(temp) == 2 or len(temp) == 3:
            return float(temp)
        elif len(temp) >= 4:
            return float(re_output.group(1)) / 1000

        return float(re_output.group(1))
