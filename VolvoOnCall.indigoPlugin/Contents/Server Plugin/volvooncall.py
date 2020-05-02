#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Communicate with VOC server."""

import logging
from datetime import timedelta
from json import dumps as to_json
from collections import OrderedDict
#from sys import argv
from urlparse import urljoin
#import asyncio

#from aiohttp import ClientSession, ClientTimeout, BasicAuth
#from aiohttp.hdrs import METH_GET, METH_POST

import requests
from requests.auth import HTTPBasicAuth

import json

import mylog

_LOGGER = logging.getLogger("Plugin.Volvo")
_LOGGER = mylog.mylogger() #Stop logging to Indigo

SERVICE_URL = "https://vocapi{region}.wirelesscar.net/customerapi/rest/v3.0/"
DEFAULT_SERVICE_URL = SERVICE_URL.format(region="")

HEADERS = {
	"X-Device-Id": "Device",
	"X-OS-Type": "Android",
	"X-Originator-Type": "App",
	"X-OS-Version": "22",
	"Content-Type": "application/json",
}

TIMEOUT = 30

METH_GET = "Get"
METH_POST = "Post"


class Connection:

	"""Connection to the VOC server."""

	def __init__(self, session, username, password, service_url=None, region=None):
		"""Initialize."""
		self._session = session
		self._auth = HTTPBasicAuth(username, password)
		self._service_url = (
			SERVICE_URL.format(region="-" + region)
			if region
			else service_url or DEFAULT_SERVICE_URL
		)
		self._state = {}
		_LOGGER.debug("Using service <%s>", self._service_url)
		_LOGGER.debug("User: <%s>", username)
		

	def _request(self, method, url, **kwargs):
		"""Perform a query to the online service."""
		try:
			_LOGGER.debug("Request for %s", url)

			if (method == "Get"):
				response = self._session.get(url,headers=HEADERS,auth=self._auth,timeout=TIMEOUT)
				
				response.raise_for_status()
				res = response.json()
				#_LOGGER.debug("Received JSON %s", res)
				return res
			elif (method == "Post"):
				response = self._session.post(url,headers=HEADERS,auth=self._auth,timeout=TIMEOUT)
				
				response.raise_for_status()
				res = response.json()
				#_LOGGER.debug("Received JSON %s", res)
				return res
		except Exception as error:
			_LOGGER.warning("Failure when communcating with the server: %s", error)
			raise

	def _make_url(self, ref, rel=None):
		return urljoin(rel or self._service_url, ref)

	def get(self, url, rel=None):
		"""Perform a query to the online service."""
		return self._request(METH_GET, self._make_url(url, rel))

	def post(self, url, rel=None, **data):
		"""Perform a query to the online service."""
		return self._request(
			METH_POST, self._make_url(url, rel), json=data
		)

	def update(self, journal=False, reset=False):
		"""Update status."""
		try:
			_LOGGER.info("Updating")
			if not self._state or reset:
				_LOGGER.info("Querying vehicles")
				self.user = self.get("customeraccounts")
				_LOGGER.debug("Account for <%s> received", self.user["username"])
				self._state = {}
				for vehicle in self.user["accountVehicleRelations"]:
					v = self.get(vehicle)
					if v.get("status") == "Verified":
						_LOGGER.warning("Getting Vehicle Attributes")
						url = v["vehicle"] + "/"
						state = self.get("attributes", rel=url)
						self._state.update({url: state})   #Adds or updates dict{url:state} to self._state dict
					else:
						_LOGGER.warning("vehicle not verified")
			#At this point, self._states{} has one entry per vehicle with ONLY the attributes, not position or status
			for vehicle in self.vehicles: #Uses class @property to return list of vehicles in self._states
				_LOGGER.warning("Updating Vehicle %s" % vehicle.unique_id)
				vehicle.update(journal=journal)
			#_LOGGER.debug("State: %s", self._state)
			return True
		except (IOError, OSError, LookupError) as error:
			_LOGGER.warning("Could not query server: %s", error)

	def update_vehicle(self, vehicle, journal=False):
		url = vehicle._url
		self._state[url].update(self.get("status", rel=url))  #Appends status and position data into self._state[url]
		self._state[url].update(self.get("position", rel=url))
		if journal:
			self._state[url].update(self.get("trips", rel=url))

	@property
	def vehicles(self):
		"""Return vehicle state."""
		return (Vehicle(self, url) for url in self._state)

	def vehicle(self, vin):
		"""Return vehicle for given vin."""
		return next(
			(
				vehicle
				for vehicle in self.vehicles
				if vehicle.vin == vin
			),
			None,
		)

	def vehicle_attrs(self, vehicle_url):
		return self._state.get(vehicle_url)
		

class Vehicle(object):
	"""Convenience wrapper around the state returned from the server."""

	def __init__(self, conn, url):
		self._connection = conn
		self._url = url

	def update(self, journal=False):
		self._connection.update_vehicle(self, journal)

	def __str__(self):
		return self.vin
		
	@property
	def displayName(self):
		return "%s (%s/%s) %s" % (
			self.regNo or "?",
			self.vehicle_type or "?",
			self.model_year or "?",
			self.vin or "?",
		)

	@property
	def attrs(self):
		return self._connection.vehicle_attrs(self._url)

	def has_attr(self, attr):
		return is_valid_path(self.attrs, attr)

	def get_attr(self, attr):
		return find_path(self.attrs, attr)

	@property
	def unique_id(self):
		return (self.regNo or self.vin).lower()

	@property
	def position(self):
		return self.attrs.get("position")

	@property
	def regNo(self):
		return self.attrs.get("registrationNumber")

	@property
	def vin(self):
		return self.attrs.get("vin")

	@property
	def model_year(self):
		return self.attrs.get("modelYear")

	@property
	def vehicle_type(self):
		return self.attrs.get("vehicleType")

	@property
	def odometer(self):
		return self.attrs.get("odometer")

	@property
	def fuel_amount_level(self):
		return self.attrs.get("fuelAmountLevel")

	@property
	def distance_to_empty(self):
		return self.attrs.get("distanceToEmpty")

	@property
	def is_honk_and_blink_supported(self):
		return self.attrs.get("honkAndBlinkSupported")

	@property
	def doors(self):
		return self.attrs.get("doors")

	@property
	def windows(self):
		return self.attrs.get("windows")

	@property
	def is_lock_supported(self):
		return self.attrs.get("lockSupported")

	@property
	def is_unlock_supported(self):
		return self.attrs.get("unlockSupported")

	@property
	def is_locked(self):
		return self.attrs.get("carLocked")

	@property
	def heater(self):
		return self.attrs.get("heater")

	@property
	def is_remote_heater_supported(self):
		return self.attrs.get("remoteHeaterSupported")

	@property
	def is_preclimatization_supported(self):
		return self.attrs.get("preclimatizationSupported")

	@property
	def is_journal_supported(self):
		return self.attrs.get("journalLogSupported") and self.attrs.get(
			"journalLogEnabled"
		)

	@property
	def is_engine_running(self):
		engine_remote_start_status = (
			self.attrs.get("ERS", {}).get("status") or ""
		)
		return (
			self.attrs.get("engineRunning")
			or "on" in engine_remote_start_status
		)

	@property
	def is_engine_start_supported(self):
		return self.attrs.get("engineStartSupported") and self.attrs.get("ERS")

	def get(self, query):
		"""Perform a query to the online service."""
		return self._connection.get(query, self._url)

	def post(self, query, **data):
		"""Perform a query to the online service."""
		return self._connection.post(query, self._url, **data)

	def call(self, method, **data):
		"""Make remote method call."""
		try:
			res = self.post(method, **data)

			if "service" not in res or "status" not in res:
				_LOGGER.warning("Failed to execute: %s", res["status"])
				return

			if res["status"] not in ["Queued", "Started"]:
				_LOGGER.warning("Failed to execute: %s", res["status"])
				return

			# if Queued -> wait?

			service_url = res["service"]
			res = self.get(service_url)

			if "status" not in res:
				_LOGGER.warning("Message not delivered")
				return

			# if still Queued -> wait?

			if res["status"] not in [
				"MessageDelivered",
				"Successful",
				"Started",
			]:
				_LOGGER.warning("Message not delivered: %s", res["status"])
				return

			_LOGGER.debug("Message delivered")
			return True
		except KeyError as error:
			_LOGGER.warning("Failure to execute: %s", error)

	@staticmethod
	def any_open(doors):
		"""
		>>> Vehicle.any_open({'frontLeftWindowOpen': False,
		...				   'frontRightWindowOpen': False,
		...				   'timestamp': 'foo'})
		False

		>>> Vehicle.any_open({'frontLeftWindowOpen': True,
		...				   'frontRightWindowOpen': False,
		...				   'timestamp': 'foo'})
		True
		"""
		return doors and any(doors[door] for door in doors if "Open" in door)

	@property
	def any_window_open(self):
		return self.any_open(self.windows)

	@property
	def any_door_open(self):
		return self.any_open(self.doors)

	@property
	def position_supported(self):
		"""Return true if vehicle has position."""
		return "position" in self.attrs

	@property
	def heater_supported(self):
		"""Return true if vehicle has heater."""
		return (
			self.is_remote_heater_supported
			or self.is_preclimatization_supported
		) and "heater" in self.attrs

	@property
	def is_heater_on(self):
		"""Return status of heater."""
		return (
			self.heater_supported
			and "status" in self.heater
			and self.heater["status"] != "off"
		)

	@property
	def trips(self):
		"""Return trips."""
		return self.attrs.get("trips")

	def honk_and_blink(self):
		"""Honk and blink."""
		if self.is_honk_and_blink_supported:
			self.call("honkAndBlink")

	def lock(self):
		"""Lock."""
		if self.is_lock_supported:
			self.call("lock")
			self.update()
		else:
			_LOGGER.warning("Lock not supported")

	def unlock(self):
		"""Unlock."""
		if self.is_unlock_supported:
			self.call("unlock")
			self.update()
		else:
			_LOGGER.warning("Unlock not supported")

	def start_engine(self):
		if self.is_engine_start_supported:
			self.call("engine/start", runtime=15)
			self.update()
		else:
			_LOGGER.warning("Engine start not supported.")

	def stop_engine(self):
		if self.is_engine_start_supported:
			self.call("engine/stop")
			self.update()
		else:
			_LOGGER.warning("Engine stop not supported.")

	def start_heater(self):
		"""Turn on/off heater."""
		if self.is_remote_heater_supported:
			#_LOGGER.info("Starting heater.")
			self.call("heater/start")
			self.update()
		elif self.is_preclimatization_supported:
			#_LOGGER.info("Starting heater.")
			self.call("preclimatization/start")
			self.update()
		else:
			_LOGGER.warning("No heater or preclimatization support.")

	def stop_heater(self):
		"""Turn on/off heater."""
		if self.is_remote_heater_supported:
			#_LOGGER.info("Stopping heater.")
			self.call("heater/stop")
			self.update()
		elif self.is_preclimatization_supported:
			#_LOGGER.info("Stopping heater.")
			self.call("preclimatization/stop")
			self.update()
		else:
			_LOGGER.warning("No heater or preclimatization support.")

	def dashboard(self, **config):
		from .dashboard import Dashboard

		return Dashboard(self, **config)

	@property
	def json2(self):
		"""Return JSON representation."""
		return to_json(
			OrderedDict(sorted(self.attrs.items())),
			indent=4,
			default=json.serialize,
		)
		
	@property
	def json(self):
		"""Return JSON representation."""
		return self._connection.vehicle_attrs(self._url)

