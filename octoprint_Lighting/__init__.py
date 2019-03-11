# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.util import RepeatedTimer
from easyprocess import EasyProcess

class LightingPlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.TemplatePlugin
		     octoprint.plugin.StartupPlugin
		     octoprint.plugin.ShutdownPlugin):

	##~~ SettingsPlugin mixin
	def __init__(self):
		self._checkTempTimer = None

	def _restartTimer(self):
		# stop the timer
		if self._checkTempTimer:
			self._logger.debug(u"Stopping Timer...")
			self._checkTempTimer.cancel()
			self._checkTempTimer = None

		# start a new timer
		interval = self._settings.get_int(['interval'])
		if self._settings.get_boolean(['enabled']) and interval:
			self._logger.debug(u"Starting Timer...")
			self._checkTempTimer = RepeatedTimer(interval, self.CheckTemps, None, None, True)
			self._checkTempTimer.start()

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/Lighting.js"],
			css=["css/Lighting.css"],
			less=["less/Lighting.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			Lighting=dict(
				displayName="Lighting Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="kylebranham67",
				repo="octoprint_Lighting",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/kylebranham67/octoprint_Lighting/archive/{target_version}.zip"
			)
		)
	
	def CheckTemps(self):
		temps = self._printer.get_current_temperatures()
		self._logger.debug(u"CheckTemps(): %r" % (temps,))
		if not temps:
			self._logger.debug(u"No Temperature Data")
			return

		for k in temps.keys():
			# example dictionary from octoprint
			# {
			#   'bed': {'actual': 0.9, 'target': 0.0, 'offset': 0},
			#   'tool0': {'actual': 0.0, 'target': 0.0, 'offset': 0},
			#   'tool1': {'actual': 0.0, 'target': 0.0, 'offset': 0}
			# }
			if k == 'bed':
				threshold_high = self._settings.get_int(['bed'])
				threshold_low = self._settings.get_int(['bed_low'])
			else:
				threshold_high = self._settings.get_int(['hotend'])
				threshold_low = self._settings.get_int(['hotend_low'])

			violation = False
			errmsg = u"TemperatureFailSafe violation, heater: {heater}: {temp}C {exp} {threshold}C"
			if threshold_high and temps[k]['actual'] > threshold_high:
				errmsg = errmsg.format(heater=k, temp=temps[k]['actual'], exp=">", threshold=threshold_high)
				violation = True

			# only check the low thresholds if we are currently printing, or else ignore it
			if self._printer.is_printing() and threshold_low and temps[k]['actual'] < threshold_low:
				errmsg = errmsg.format(heater=k, temp=temps[k]['actual'], exp="<", threshold=threshold_low)
				violation = True

			if violation:
				# alert the user
				self._logger.error(errmsg)
				self._plugin_manager.send_plugin_message(__plugin_name__, dict(type="popup", msg=errmsg))

				env = {}
				env["TEMPERATURE_FAILSAFE_FAULT_TOOL"] = str(k)
				env["TEMPERATURE_FAILSAFE_FAULT_HIGH_THRESHOLD"] = str(threshold_high)
				env["TEMPERATURE_FAILSAFE_FAULT_LOW_THRESHOLD"] = str(threshold_low)

				# place the temperatures into an environment dictionary to pass to the remote program
				for t in temps.keys():
					env["TEMPERATURE_FAILSAFE_%s_ACTUAL" % t.upper()] = str(temps[t]['actual'])
					env["TEMPERATURE_FAILSAFE_%s_TARGET" % t.upper()] = str(temps[t]['target'])

				#self._executeFailsafe(env)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Lighting Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = LightingPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

