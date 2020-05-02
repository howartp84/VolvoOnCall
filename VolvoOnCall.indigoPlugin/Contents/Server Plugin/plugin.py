#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# VolvoOnCall plugin for indigo
#
# This plugin uses the python API published by Erik Eriksson
# https://github.com/molobrakos/volvooncall
#
# Based on sample code that is:
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo
import volvooncall

import requests
import traceback

import random

import time

from math import sin, cos, sqrt, atan2, radians

from urllib2 import HTTPError

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", True)
		self.version = pluginVersion
		
		self.session = requests.Session()
		
		self.vehicles = []
		#self.debug = True
		
		self.states = {}
		
		self.strstates = {}
		self.numstates = {}
		self.boolstates = {}
		
		self.resetStates = False
		
		self.cmdStates = {}

		self.cmdStates["set_valet_mode"] = ""

	def startups(self):
		self.conn = volvooncall.Connection(self.session, self.pluginPrefs['username'],self.pluginPrefs['password'])
		self.conn.update()
		for v in self.conn.vehicles:
			v.update()
			self.vehicles.append(v)
			self.debugLog(v.json)
			
		#for w in self.vehicles:
			#self.errorLog(w.json)

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		# Since the dialog closed we want to set the debug flag - if you don't directly use
		# a plugin's properties (and for debugLog we don't) you'll want to translate it to
		# the appropriate stuff here.
		if not userCancelled:
			self.debug = valuesDict.get("showDebugInfo", False)
			if self.debug:
				indigo.server.log("Debug logging enabled")
			else:
				indigo.server.log("Debug logging disabled")

	def deviceStartComm(self, dev):
		self.getVehicles()
		self.debugLog("Device ID Started: %s" % dev.id)
		vehicleId = dev.ownerProps['car'] #VIN
		statusName="update"
		self.vehicleStatus2(statusName,vehicleId,dev.id)

	def getDeviceStateList(self, dev): #Override state list
		stateList = indigo.PluginBase.getDeviceStateList(self, dev)
		if stateList is not None:
#			for key in self.states.iterkeys():
#				dynamicState1 = self.getDeviceStateDictForStringType(key, key, key)
#				stateList.append(dynamicState1)
			#self.debugLog(str(stateList))
			for key in self.strstates.iterkeys():
				if ((self.resetStates) and (key in stateList)):
					stateList.remove(key)
				dynamicState1 = self.getDeviceStateDictForStringType(key, key, key)
				stateList.append(dynamicState1)
			for key in self.numstates.iterkeys():
				if ((self.resetStates) and (key in stateList)):
					stateList.remove(key)
				dynamicState1 = self.getDeviceStateDictForNumberType(key, key, key)
				stateList.append(dynamicState1)
			for key in self.boolstates.iterkeys():
				if ((self.resetStates) and (key in stateList)):
					stateList.remove(key)
				dynamicState1 = self.getDeviceStateDictForBoolTrueFalseType(key, key, key)
				stateList.append(dynamicState1)
		return sorted(stateList)

	def getVehicles(self):
		if not self.vehicles:
			indigo.server.log("Fetching vehicles...")
			self.debugLog("Fetching vehicles...")
			try:
				self.conn = volvooncall.Connection(self.session, self.pluginPrefs['username'],self.pluginPrefs['password'])
				self.conn.update(True)
				for v in self.conn.vehicles:
					v.update() #This happens automatically in conn.update
					self.vehicles.append(v)
					#self.debugLog(v.json)
				indigo.server.log("%i vehicles found" % len(self.vehicles))
				#self.debugLog(self.vehicles)
				for v in self.vehicles:
					self.debugLog(u"Vehicle %s: %s" % (v,v.regNo))
			except Exception as e:
				self.errorLog(e)
				self.errorLog("Error issuing command: {} {}".format(commandName,str(data)))
				self.errorLog("Plugin version: {}".format(self.version))
				self.debugLog(traceback.format_exc())
		#self.debugLog("Returning vehicle list: %s" % self.vehicles)
		return self.vehicles

	# Generate list of cars	
	def carListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		cars = [(k.vin, "%s (%s)" % (k.regNo, k.vin))
				for k in self.getVehicles()]
		self.debugLog("carListGenerator: %s" % str(cars))
		return cars

	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
		self.debugLog("Device ID: %s" % devId)		
		vehicleId = valuesDict['car'] #VIN
		statusName="update"
		self.vehicleStatus2(statusName,vehicleId,devId)
		return True
		
	### ACTIONS
	def validateActionConfigUi(self, valuesDict, typeId, actionId):
		if typeId=='set_charge_limit':
			try:
				percent = int(valuesDict['percent'])
				if percent > 100 or percent < 50:
					raise ValueError
				valuesDict['percent'] = percent
			except ValueError:
				errorsDict = indigo.Dict()
				errorsDict['percent'] = "A percentage between 50 and 100"
				return (False, valuesDict, errorsDict)
		return (True, valuesDict)
	
	def vehicleCommand(self, action, dev):
		vehicleId = dev.pluginProps['car']
		commandName = action.pluginTypeId
		indigo.server.log("Volvo command %s for vehicle %s" % (commandName, vehicleId))
		try:
			vehicle = self.conn.vehicle(vehicleId) #Get vehicle object from VIN
		except KeyError:
			self.errorLog(u"Vehicle ID %s not recognised.  Please edit your Volvo Vehicle device and re-select the appropriate car." % vehicleId)
			dev = indigo.devices[devId]
			self.debugLog(u"Indigo device '%s' holds vehicleId of %s but this no longer exists in the vehicle list returned by Volvo." % (dev.name,vehicleId))
			return
		data = action.props
		#self.debugLog(data)
		try:
			if commandName == "start_heater":
				vehicle.start_heater()
			elif commandName == "stop_heater":
				vehicle.stop_heater()
		except Exception as e:
			self.errorLog(e)
			self.errorLog("Error issuing command: {} {}".format(commandName,str(data)))
			self.errorLog("Plugin version: {}".format(self.version))
			self.debugLog(traceback.format_exc())

	def vehicleStatus(self, action, dev):
		vehicleId = dev.pluginProps['car']
		statusName = action.pluginTypeId
		#self.debugLog(str(dev))
		if (statusName == ""):
			return
		self.vehicleStatus2(statusName,vehicleId,dev.id)
		
	def vehicleStatus2(self,statusName,vehicleId,devId):
		indigo.server.log("Volvo request %s for vehicle %s: Initialising" % (statusName, vehicleId))
		try:
			vehicle = self.conn.vehicle(vehicleId) #Get vehicle object from VIN
		except Exception as e:
			self.errorLog(e)
			self.errorLog(u"Vehicle ID %s not recognised.  Please edit your Volvo Vehicle device and re-select the appropriate car." % vehicleId)
			dev = indigo.devices[devId]
			self.debugLog(u"Indigo device '%s' holds vehicleId of %s but this no longer exists in the vehicle list returned by Volvo." % (dev.name,vehicleId))
			return
		dev = indigo.devices[devId]
		
		#self.debugLog(vehicle)
		
		#self.debugLog(statusName)
		
		self.response = "Incomplete"
		try:
			self.response = vehicle.update()
		except HTTPError as h:
			self.errorLog(h)
			self.errorLog("Timeout retrieving status: {}".format(statusName))
			self.debugLog(traceback.format_exc())
		except Exception as e:
			self.errorLog(e)
			self.errorLog("Timeout retrieving status: {}".format(statusName))
			self.debugLog(traceback.format_exc())
		#self.debugLog(u"Response: %s" % str(self.response)) #Will be None as it doesnt return
	
		for k in vehicle.json:
			if (k == "VIN"):
				continue
			v = vehicle.json[k]
			if type(v) == dict:
				for innerk in v:
					if type(v[innerk]) == dict:
						for innerinnerv in v[innerk]:
							#self.debugLog("%s_%s_%s => %s (%s 1)" % (k,innerk,innerinnerv,v[innerk][innerinnerv],type(v[innerk][innerinnerv])))
							self.updateTheState("%s_%s_%s" % (k,innerk,innerinnerv),v[innerk][innerinnerv],dev)
					else:
						#self.debugLog("%s_%s => %s (%s2)" % (k,innerk,v[innerk],type(v[innerk])))
						self.updateTheState("%s_%s" % (k,innerk),v[innerk],dev)
			else:
				#self.debugLog("%s => %s (%s3)" % (k,v,type(v)))
				self.updateTheState(k,v,dev)

		if (self.resetStates):
			indigo.server.log("Volvo request %s for vehicle %s: New states found - reinitialising" % (statusName, vehicleId))
			dev.stateListOrDisplayStateIdChanged()
			self.resetStates = False
			self.vehicleStatus2(statusName,vehicleId,devId) #Re-do this request now the states are reset
			return
		indigo.server.log("Volvo request %s for vehicle %s: Completed" % (statusName, vehicleId))

		self.latLongHome = dev.ownerProps.get("latLongHome","37.394838,-122.150389").split(",")
		self.latLongWork = dev.ownerProps.get("latLongWork","37.331820,-122.03118").split(",")
		fromHomeKm = self.getDistance(dev.states['position_latitude'],dev.states['position_longitude'],float(self.latLongHome[0]),float(self.latLongHome[1]))
		fromWorkKm = self.getDistance(dev.states['position_latitude'],dev.states['position_longitude'],float(self.latLongWork[0]),float(self.latLongWork[1]))
		fromHomeM = fromHomeKm * 0.62137119223733
		fromWorkM = fromWorkKm * 0.62137119223733
		dev.updateStateOnServer("distanceFromHomeKm",round(fromHomeKm,2), uiValue=str(round(fromHomeKm,2))+"km")
		dev.updateStateOnServer("distanceFromWorkKm",round(fromWorkKm,2), uiValue=str(round(fromWorkKm,2))+"km")
		dev.updateStateOnServer("distanceFromHomeM",round(fromHomeM,2), uiValue=str(round(fromHomeM,2))+"m")
		dev.updateStateOnServer("distanceFromWorkM",round(fromWorkM,2), uiValue=str(round(fromWorkM,2))+"m")
		
	def updateTheState(self,inKey,inValue,dev):
		if (inKey in dev.states) and (self.resetStates == False):
			if (type(inValue) is list):
				inValue = ','.join(map(str, inValue)) #Join all elements into a string
			#self.debugLog(str(type(inValue)))
			dev.updateStateOnServer(inKey,inValue)
			if (inKey == dev.ownerProps.get("stateToDisplay","")):
				if (inKey == "fuelAmountLevel"):
					dev.updateStateOnServer("displayState",inValue,uiValue="%s%%" % inValue)
				else:
					dev.updateStateOnServer("displayState",inValue)
		else:
			#self.debugLog("New states found - recreating state list...")
			self.resetStates = True #We obviously need to reset states if we've got data for one that doesn't exist
			if (inValue == None):
				self.strstates[inKey] = inValue
			elif (type(inValue) is float):
				self.numstates[inKey] = inValue
			elif (type(inValue) is int):
				self.numstates[inKey] = inValue
			elif (type(inValue) is bool):
				self.boolstates[inKey] = inValue
			elif (type(inValue) is str):
				self.strstates[inKey] = inValue
			elif (type(inValue) is unicode):
				self.strstates[inKey] = inValue
			else:
				self.strstates[inKey] = inValue

	def getDistance(self,atLat,atLong,fromLat,fromLong):
		# approximate radius of earth in km
		R = 6373.0

		lat1 = radians(float(atLat))   #Where is vehicle at
		lon1 = radians(float(atLong))
		lat2 = radians(float(fromLat)) #Where are we testing from, eg Home
		lon2 = radians(float(fromLong))

		dlon = lon2 - lon1
		dlat = lat2 - lat1

		a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
		c = 2 * atan2(sqrt(a), sqrt(1 - a))

		distance = R * c

		#self.debugLog(u"Result: %s" % distance)
		#self.debugLog(u"Should be: 278.546 km")
		return distance
	
	def runConcurrentThread(self):
		try:
			while True:
				if not self.vehicles:
					self.debugLog("runThread: Getting vehicles")
					self.getVehicles()
				else:
					self.debugLog("runThread: Sleeping")
				self.sleep(60) # in seconds
		except self.StopThread:
			# do any cleanup here
			pass