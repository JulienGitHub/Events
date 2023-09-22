import requests
import time
import json
import glob, os
import csv
import ftplib
from discordwebhook import Discord
from datetime import datetime, timedelta
import shutil
import geopy.distance
from geopy.geocoders import Nominatim
import tweepy

class webHook:
	def __init__(self, url, country, state, guid, types, latitude, longitude, distance, unit):
		self.url = url
		self.country = country
		self.state = state
		self.guid = guid
		self.types = types
		self.latitude = latitude
		self.longitude = longitude
		self.distance = distance
		self.distanceUnit = unit

def isInZone(longitude, latitude):
	global squares
	for square in squares:
		if(longitude >= square[0] and longitude <= square[1] and latitude >= square[2] and latitude <= square[3]):
			return True
	return False

while(True):
	try:
		#data is being saved in a csv before being pushed in a sql database (don't judge me, I had no access to the website DB outside of the website, this script is running at home)
		mainTable = open("main.csv", "w", encoding='utf-8')
		
		#removing the previous json
		fileList = glob.glob('./*.json')
		for filePath in fileList:
			try:
				os.remove(filePath)
			except:
				print("Error while deleting file : ", filePath)

		#definition of the areas of interest lat/long on the map, trying to only scan part of the earth where events could be
		squares = [[120, 180, -50, -10], [-30, 40, 30, 80], [-170, -50, 50, 80], [-130, -50, 30, 50], [-120, -60, 10, 30], [-90, -30, -60, 10]]
		
		#scanning the event map, saving each json as lat_long.json
		tic = time.perf_counter()
		for longitude in range(-180, 180, 5):
			for latitude in range(-90, 90, 3):
				if(isInZone(longitude, latitude)):
					#print(str(latitude)+'_'+str(longitude)+' is in zone')
					strReq = 'https://op-core.pokemon.com/api/v2/event_locator/search/?latitude='+str(latitude)+'&longitude='+str(longitude)+'&distance=250'
					req = requests.get(strReq)
					if(req.status_code == 200 and len(req.text)>2):
						with open(str(latitude)+'_'+str(longitude)+'.json', 'w', encoding="utf-8") as f:
							f.write(req.text)
						print(str(latitude)+'_'+str(longitude)+' done')
		toc = time.perf_counter()
		print(toc - tic)
		
		#backing up the webhooks.json : it's where the already sent events are stored for each Discord server, if lost, would send every event of interest once more...
		origfile = './webhooks/webhooks.json'
		backupfile = origfile + "." + datetime.now().strftime("%Y-%m-%d_%H%M%S")
		shutil.copy(origfile, backupfile)

		#creating the './webhooks/webhooks.json' path/file if it does not exists
		webhooksFile = './webhooks'
		if not os.path.exists(webhooksFile):
			os.makedirs(webhooksFile)
		webhooksFile = './webhooks/webhooks.json'
		isFile = os.path.isfile(webhooksFile)
		if (not isFile):
			with open(webhooksFile, 'w') as fp:
				pass
		else:
			print(f'The {webhooksFile} file exists.')

		#list of webhooks configured
		webhooks = []
		with open(webhooksFile, 'r', encoding="utf-8") as json_file:
			jsonWebhooks = json.load(json_file)
			for hook in jsonWebhooks:
				webhooks.append(webHook(hook.get('url'), hook.get('country'), hook.get('state'), hook.get('guid'), hook.get('types'), hook.get('latitude') or 999, hook.get('longitude') or 999, hook.get('distance') or 0, hook.get('distanceUnit') or 'km'))
		
		#Adding new hooks
		try:
			#missing : retrieving the newly registered webhooks, placing them in ./new/

			fileList = glob.glob('./new/*.json')
			for filePath in fileList:
				try:
					if(os.path.isfile(filePath)):
						with open(filePath, 'r', encoding="utf-8") as json_file:
							jsonNewWebhooks = json.load(json_file)
							for hook in jsonNewWebhooks:
								webhooks.append(webHook(hook.get('url'), hook.get('country'), hook.get('state'), hook.get('guid'), hook.get('types'), hook.get('latitude') or 999, hook.get('longitude') or 999, hook.get('distance') or 0, hook.get('distanceUnit') or 'km'))
						os.rename(filePath, filePath+'.done')
				except:
					print("Error while deleting file : ", filePath)
		except Exception as e: print(e)
		
		events = []

		cups = 0
		challenges = 0
		prerelease = 0
		premier = 0
		midchal = 0
		gochall = 0
		discordSent = 0

		for f_name in glob.glob('./*.json'):
			with open(f_name, 'r', encoding="utf-8") as json_file:
				print(f_name)
				try:
					json_data = json.load(json_file)
					for activity in json_data['activities']:
						guid = activity['guid']
						if(guid not in events):
							events.append(guid)
							tags = activity['tags']
							products = activity['products']
							interest = False
							activity_type = ""
							Type = ""
							if("league_cup" in tags and products != None and 'tcg' in products):
								#print("League Cup")
								interest = True
								activity_type = "League Cup"
								cups+=1
								Type = "cup"
							if("prerelease" in tags and products != None and 'tcg' in products):
								#print("League Cup")
								interest = True
								activity_type = "Pre Release"
								prerelease += 1
								Type = "pre"
							if("premier_challenge" in tags and products != None and 'vg' in products):
								#print("League Cup")
								interest = True
								activity_type = "Premier Challenge"
								premier += 1
								Type = "pchal"
							if("midseason_showdown" in tags and products != None and 'vg' in products):
								#print("League Cup")
								interest = True
								activity_type = "Midseason Showdown"
								midchal += 1
								Type = "midshow"
							if("league_challenge" in tags and products != None and 'tcg' in products):
								#print("League Challenge")
								interest = True
								activity_type = "League Challenge"
								challenges += 1
								Type = "chall"
							if("championship_series" in tags and products != None and 'pgo' in products):
								#print("League Challenge")
								interest = True
								activity_type = "GO Challenge"
								gochall += 1
								Type = "go"
							if(interest):
								mainTable.write(activity_type+";")
								date = activity['when'].split('T')[0].split('-')
								
								latitude = activity['address']['latitude'] or 999
								longitude = activity['address']['longitude'] or 999

								mainTable.write(activity['name'] or "")
								mainTable.write(";")
								mainTable.write(str(date[0]) + '-'+ str(date[1])+ '-'+ str(date[2]) or "")
								mainTable.write(";")
								mainTable.write(activity['address']['name'] or "")
								mainTable.write(";")
								mainTable.write(activity['address']['street_address'] or "")
								mainTable.write(";")
								mainTable.write(activity['address']['state'] or "")
								mainTable.write(";")
								mainTable.write(activity['address']['city'] or "")
								mainTable.write(";")
								mainTable.write(activity['address']['postal_code'] or "")
								mainTable.write(";")
								mainTable.write(activity['address']['country_code'] or "")
								mainTable.write(";")
								mainTable.write(activity['pokemon_url'] or "")
								mainTable.write(";")
								mainTable.write(activity['guid'] or "")
								mainTable.write(";")
								mainTable.write(str(activity['address']['latitude']) or "")
								mainTable.write(";")
								mainTable.write(str(activity['address']['longitude']) or "")
								mainTable.write(";")
								mainTable.write(str(activity['when']) or "")
								mainTable.write(";")
								mainTable.write("")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("0")
								mainTable.write(";")
								mainTable.write("")
								mainTable.write(";")
								mainTable.write("")
								mainTable.write(";")
								mainTable.write("")
								mainTable.write("\n")
								
								for hook in webhooks:
									withinDistance = False
									if(hook.latitude != 999):
										activityCoord = (latitude, longitude)
										hookCoord = (hook.latitude, hook.longitude)
										dist = 0
										if(hook.distanceUnit in 'miles'):
											dist = geopy.distance.distance(activityCoord, hookCoord).miles
										else:
											dist = geopy.distance.distance(activityCoord, hookCoord).km
										if(dist < hook.distance):
											withinDistance = True
									if(Type in hook.types):
										bSend = False
										if(withinDistance):
											if(hook.country == None):
												bSend = True
											else:
												if(hook.country != None and activity['address']['country_code'] != None and activity['address']['country_code'] in hook.country):
													if(hook.state == None):
														bSend = True
													else:
														if (activity['address']['state'] != None and activity['address']['state'] in hook.state):
															bSend = True
										else:
											if(hook.latitude == 999):
												if(hook.country != None and activity['address']['country_code'] != None and activity['address']['country_code'] in hook.country):
													if(hook.state == None):
														bSend = True
													else:
														if (activity['address']['state'] != None and activity['address']['state'] in hook.state):
															bSend = True
										if(bSend):										
											color = 0
											colorID = "8"
											#using pokemon images for the discord message (maybe not recommended)
											if("Challenge" in activity_type):
												pic = "https://events.pokemon.com/images/league-challenge.png"
												color = 255
												colorID = "9"
											if("Cup" in activity_type):
												pic = "https://events.pokemon.com/images/league-cup.png"
												color = 16711680
												colorID = "11"
											if("Release" in activity_type):
												pic = "https://events.pokemon.com/images/prerelease.png"
												color = 16776960
												colorID = "5"
											if("Premier" in activity_type):
												pic = "https://events.pokemon.com/images/premier-challenge.png"
												color = 3316516
												colorID = "2"
											if("Midseason" in activity_type):
												pic = "https://events.pokemon.com/images/midseason-showdown.png"
												color = 15105570
												colorID = "8"
											if("GO" in activity_type):
												pic = "https://events.pokemon.com/images/premier-challenge.png"
												color = 9440693
												colorID = "1"
											
											
											if(guid not in hook.guid):
												discord = Discord(url=hook.url)
												try:
													a = 2
													discord.post(	embeds=[
																	{
																		"author": {
																			"name": activity_type,
																			"url": (activity['pokemon_url'] or ""),
																			"icon_url": pic,
																		},
																		"title": (activity['name'] or "")+"\n"+activity['pokemon_url'],
																		"description": (activity['address']['name'] or ""),
																		"color":color,
																		"fields": [
																			{"name": "Country", "value": (activity['address']['country_code'] or ""), "inline": True},
																			{"name": "State", "value": (activity['address']['state'] or ""), "inline": True},
																			{"name": "Address", "value": (activity['address']['street_address'] or ""), "inline": True},
																			{"name": "Date", "value": (str(date[0]) + '-'+ str(date[1])+ '-'+ str(date[2]) or ""), "inline": True},
																			{"name": "Postal Code", "value": (activity['address']['postal_code'] or ""), "inline": True},
																			{"name": "City", "value": (activity['address']['city'] or ""), "inline": True},
																		]															
																	}
																],
															)
													hook.guid.append(guid)
													discordSent+=1
												except Exception as e: print(e)
											
											a = 2
										else:
											if(guid in hook.guid):
												hook.guid.remove(guid)
								
						else:
							pass #event already present
							
				except Exception as e: print(e)
		mainTable.close()

		#saving webhooks and the data they received
		with open('./webhooks/webhooks.json', "w") as file:
			json.dump([obj.__dict__ for obj in webhooks], file)

		#missing : add main.csv to internal database

	except Exception as e: print(e)

	now = datetime.now()

	current_time = now.strftime("%H:%M:%S")
	print("Current Time =", current_time)
	print("Sleeping 30 minutes")
	time.sleep(30*60)