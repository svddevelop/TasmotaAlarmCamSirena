"""
<plugin
	key="tMQTTalarm"
	name="Tasmota MQTT Alarm Integration"
	author="S.Pfaffenrot"
	version="1.1.0"
	externallink="https://github.com/svddevelop/TasmotaAlarmCamSirena">
	<description>
		Tasmota MQTT Integration Plugin
		<p>This plugin is designed to work with "Tasmota MQTT Alarm Integration" modules.
		The module has switch1, which activates siren and camera signals when a sensor is triggered. There is switch2, which when toggled activates the siren and camera of the current device. There is switch3, which always shows the current sensor state.</p>
		
		<p>The address "Domoticz IP" must be in trusted network (see paramaters in settings of Domoticz).</p>
		
		<p>All inter-module settings are stored in the "Alarm settings" parameter. The string consists of several parameters separated by a semicolon ";". Elements within lists are separated by a comma ",". Optional parameter "master" must be set if you want to switch all devices from one (master).</p>
		
		<p>Suppose there are two modules controlling two different doors, but the siren is installed on only one module. In the "modules" parameter, all Tasmota device identifiers that perform this function are listed.</p>
		<p>Example string: alarmmodules=AC56DA,E7891A;alarmmaster=AC56DA;</p>
	</description>
	<params>
		<!-- Domoticz API -->
		<param field="Address" label="Domoticz http-IP" width="200px" required="true" default="http://username:password@127.0.0.1:8080/"/>
		<param field="Password" label="Domoticz Password" width="200px" required="false" password="true"/>

		<!-- MQTT Broker -->
		<param field="Mode1" label="MQTT Server" width="200px" required="true" default="127.0.0.1"/>
		<param field="Port" label="MQTT Port" width="80px" required="true" default="1883"/>
		<param field="Username" label="MQTT Username" width="200px" required="false"/>
		<param field="Mode4" label="MQTT Password" width="200px" required="false" password="true"/>

		<!-- Alarm control -->
		<param field="Mode2" label="Alarm settings" width="600px" required="true" default="alarmmodules=;alarmmaster=;"/>

		<!-- Debug -->
		<param field="Mode6" label="Debug" width="75px">
			<options>
				<option label="True" value="Debug"/>
				<option label="False" value="Normal" default="true"/>
			</options>
		</param>
	</params>
</plugin>
"""
errmsg = ""
try:
	import Domoticz
except Exception as e:
		pass #Domoticz.Error(f"onStart Mode2: {e}")
# try:
	# from tasmota import Handler, setTasmotaDebug
# except Exception as e:
	# errmsg += " tasmota::Handler import error: "+str(e)
		
import json
import paho.mqtt.client as mqtt
import requests

#
# https://wiki.domoticz.com/Domoticz_API/JSON_URL%27s#Create_a_device
#
# send notification over EMail: /json.htm?type=command&param=sendnotification&subject='ATTENTION: communication timeout'&body='Please check and restore the connection '
#
#


#class BasePlugin:
class Plugin:
	def __init__(self):
		self.mqttClient = None
		self.idx_cache = {}	 # ключ: "cmnd/tasmota_XXXXXX/SwitchY" → IDX
		self.debug = False
		self.alarm_modules = {}	 # идентификаторы устройств
		self.alarm_switch = {}	# Switch3-couples [device_id]-[idx] for all included devices 
		self.alarm_watch = {}	# Switch1-couples [device_id]-[idx] for all included devices
		self.alarm_test = {}	# Switch2-couples [device_id]-[idx] for all included devices
		self.alarm_master = {}	# Master [device_id]-[idx]
		#self.master = ""
		self.alarm_master_switch1_idx = -1
		self.alarm_master_switch2_idx = -1
		self.alarm_master_refs = {}
		self.public_ip = ""
		#tasmotaHandler = None
		
		global Devices
		global devices
		#Devices = devices
	
	def onStart(self):
		if Parameters["Mode6"] == "Debug":
			self.debug = True
			Domoticz.Debugging(1)
		Domoticz.Log(f"Devices::onStart: Parameters: {Devices} ")
		

		self.mqttClient = mqtt.Client()
		self.mqttClient.on_connect = self.onMQTTConnect
		self.mqttClient.on_disconnect = self.onMQTTDisconnect
		self.mqttClient.on_message = self.onMQTTMessage
		
		if Parameters["Username"].strip():
			self.mqttClient.username_pw_set(Parameters["Username"], Parameters["Mode4"])
		
		# получить список устройств из modules
		
		if Parameters["Mode2"].strip():
			try:
				modules = Parameters["Mode2"]
				# self.alarm_modules = modules.split("=", 1)[-1].rstrip(";").split(",")
				
				parts = modules.split(';')
				
				for part in parts:
					part = part.strip()
					if not part:
						continue
						
					if part.startswith('alarmmodules='):
						value = part[13:].strip()		   # убираем "alarmmodules="
						self.alarm_modules = [m.strip() for m in value.split(',') if m.strip()]
						
					elif part.startswith('alarmmaster='):
						value = part[12:].strip()		   # убираем "alarmmaster="
						self.alarm_master = [m.strip() for m in value.split(',') if m.strip()]
						self.alarm_master_switch1_idx = self.find_alarmdevice_idx(self.alarm_master[0], 'POWER1')
						self.alarm_master_switch2_idx = self.find_alarmdevice_idx(self.alarm_master[0], 'POWER2')
						Domoticz.Log(f"AMaster: Switch1:{self.alarm_master_switch1_idx} Switch2:{self.alarm_master_switch2_idx}")
						for a_m in self.alarm_modules:
							if a_m != self.alarm_master[0]:
								s_s1_idx = self.find_alarmdevice_idx(a_m, 'POWER1')
								self.alarm_master_refs.setdefault(self.alarm_master_switch1_idx, []).append(s_s1_idx)
								s_s2_idx = self.find_alarmdevice_idx(a_m, 'POWER2')
								self.alarm_master_refs.setdefault(self.alarm_master_switch2_idx, []).append(s_s2_idx)
						
						
						
				Domoticz.Log(f"Modules:{self.alarm_modules} AMaster:{self.alarm_master} Refs:{self.alarm_master_refs}")
			except Exception as e:
				Domoticz.Error(f"onStart Mode2: {e}")

		self.load_devices_cache()
		
		try:
			MqttAddress = 'localhost'
			MqttPort = 1883
			MqttAddress = Parameters["Mode1"].strip()
			MqttPort = int(Parameters["Port"])
			self.mqttClient.connect(MqttAddress, MqttPort, 60)
			self.mqttClient.loop_start()
			Domoticz.Log("MQTT connection initiated")
		except Exception as e:
			Domoticz.Error(f"MQTT connection failed: {e} {MqttAddress}")
			
		# try:
			# self.tasmotaHandler = Handler("%prefix%/%topic%|%topic%/%prefix%".strip().split('|'), "cmnd".strip(
				# ), "stat".strip(), "tele".strip(), self.mqttClient, Devices)
			# self.tasmotaHandler.debug(True)
		# except Exception as e:
			# Domoticz.Error(f"tasmotaHandler failed: {e} ")
			
		self.refresh_public_ip()
		
	def load_devices_cache(self):
		DzAddress = '127.0.0.1'
		DzAddress = Parameters['Address']
		DzPassword = Parameters["Password"]
		
		url = f"{DzAddress}/json.htm?type=command&param=getdevices&filter=light&used=true&order=Name"
		
		#Domoticz.Log(f"Loading devices from Domoticz API: {url}")

		try:
			r = requests.get(url, timeout=10, verify=False)
			if r.status_code != 200:
				Domoticz.Error(f"Failed to load devices: HTTP {r.status_code}")
				return
			
			data = r.json()
			if data.get("status") != "OK":
				Domoticz.Error("API returned not OK status")
				return
			
			self.idx_cache.clear()
			for dev in data.get("result", []):
				desc = dev.get("Description", "").strip()
				if not desc:
					continue
			
				try:
					desc_json = json.loads(desc)
					topic = desc_json.get("Topic")
					#Domoticz.Log(f"topic = {topic}")
					device = desc_json.get("Device")
					#Domoticz.Log(f"device = {device}")
					command = desc_json.get("Command")
					#Domoticz.Log(f"command = {command} {dev.get("idx")}")
					modulefound = 0
					#Domoticz.Log(f"modules = {self.alarm_modules}")
					for module in self.alarm_modules:
						#Domoticz.Log(f"module = {module}")
						if topic.find(module) > -1:
							modulefound = 1
							break
					
						
					has_sw3_fm = self.has_switch3_for_module(module)
					if modulefound == 1 and has_sw3_fm > 0 :
						self.alarm_switch[module] = has_sw3_fm
						
						if command == 'POWER1' and topic.find(module) > 0 :
							#Domoticz.Log(f"command = {command} {dev.get("idx")} {dev.get("CustomImage")}")
							self.alarm_watch[module] = dev.get("idx")
							self.alarm_watch[dev.get("idx")] = module
							#if dev.get("CustomImage") != 13:
							#	Domoticz.Log(f"need to change CustomImage = {command} {dev.get("idx")} {dev.get("CustomImage")}")
						if command == 'POWER2' and topic.find(module) > 0 :
							#Domoticz.Log(f"command = {command} {dev.get("idx")} {dev.get("CustomImage")}")
							self.alarm_test[module] = dev.get("idx")
							self.alarm_test[dev.get("idx")] = module
							#if dev.get("CustomImage") != 13:
							#	Domoticz.Log(f"need to change CustomImage = {command} {dev.get("idx")} {dev.get("CustomImage")}")
							
					#Domoticz.Log(f"has_sw3_fm({module}):{has_sw3_fm}  {topic.find(module)}")
					#Domoticz.Log(f"self.alarm_switch:({self.alarm_switch})")
					if has_sw3_fm == 0:
						Domoticz.Log(f"create AlarmSwitch3_{module}")
						self.create_and_setup_alarm_switch(module)
						
					#if topic and device and dev.get("idx"):
					#		key = f"{topic}/{device}"
					#		self.idx_cache[key] = int(dev["idx"])
					#		Domoticz.Log(f"Cached: {key} → IDX {dev['idx']} ({dev['Name']})")
				except json.JSONDecodeError:
					continue
			
			#Domoticz.Log(f"Device cache loaded: {len(self.idx_cache)} entries")
			Domoticz.Log(f"Device cache Alarm switches:{self.alarm_switch} watch:{self.alarm_watch} test:{self.alarm_test}")
			
		except Exception as e:
			Domoticz.Error(f"Error loading devices: {e}")
			
	def create_and_setup_alarm_switch(self, module_id: str) -> int:

		if not module_id:
			Domoticz.Error("create_and_setup_alarm_switch: module_id ist empty")
			return 0


		dz_base_url = Parameters["Address"]
		hw_idx = self.get_virtual_devices_hardware_idx()


		create_url = (
			f"{dz_base_url}/json.htm?"
			f"type=command&"
			f"param=createdevice&"
			f"sensorname=AlarmSwitch_{module_id}&"
			f"devicetype=244&"
			f"devicesubtype=73&"
			f"switchtype=0&"
			f"used=true&"
			f"customimage=34&"
			f"HardwareID=3&"
			f"HardwareDisabled=false&"
			f"HardwareTypeVal=94&"
			f"HardwareName=Tasmota%20device&"
			f"HardwareType=TMQTTAS&"
			f"idx={hw_idx}"
		)

		try:
			r = requests.get(create_url, timeout=10, verify=False)
			r.raise_for_status()

			data = r.json()
			if data.get("status") != "OK" or "idx" not in data:
				Domoticz.Error(f"Создание устройства не удалось: {data}")
				return 0

			idx = int(data["idx"])
			Domoticz.Log(f"registered new device AlarmSwitch_{module_id} → idx = {idx}")

		except Exception as e:
			Domoticz.Error(f"Mistake on the device creation {module_id}: {e}")
			return 0

		#Domoticz.Log("stp2")
		description_raw = (
			'{\n'
			f'%09"Topic":%20"cmnd/tasmota_{module_id}",\n'
			f'%09"Device":%20"Switch3",\n'
			f'%09"Type":%20"2",\n'
			f'%09"Name":%20"AlarmCam_{module_id}"\n'
			'}'
		)

		update_url = (
			f"{dz_base_url}/json.htm?"
			f"type=command&"
			f"param=setused&"
			f"used=true&"
			f"switchtype=0&"
			f"name=AlarmSwitch_{module_id}&"
			f"description={description_raw}&"
			f"customimage=34&"
			f"HardwareDisabled=false&"
			f"HardwareTypeVal=94&"
			f"HardwareName=Tasmota%20device&"
			f"HardwareType=TMQTTAS&"
			f"idx={idx}"
		)
		#Domoticz.Log("stp4")

		try:
			#Domoticz.Log(f"Update URL:{update_url}")
			r = requests.get(update_url, timeout=10, verify=False)
			r.raise_for_status()

			data = r.json()
			if data.get("status") != "OK":
				Domoticz.Error(f"Update device idx={idx} does not hapens: {data}")
				return 0

			Domoticz.Log(f"Update for device was successed idx={idx} ({module_id})")
			return idx

		except Exception as e:
			Domoticz.Error(f"Mistake on update for idx={idx}: {e}")
			return 0			
			
	def has_switch3_for_module(self, module_id: str) -> int:

		#Domoticz.Log("has_switch3_for_module() ")
		expected_topic = f"cmnd/tasmota_{module_id}"
		expected_json_snippet = {
			"Topic": expected_topic,
			"Device": "Switch3",
			"Type": 2
		}
		module_topic = 'cmnd/tasmota_'+module_id
		DzAddress = '127.0.0.1'
		DzAddress = Parameters['Address']
		DzPassword = Parameters["Password"]
		
		url = f"{DzAddress}/json.htm?type=command&param=getdevices&filter=light&used=true&order=Name"
		
		#Domoticz.Log(f"Loading devices from Domoticz API: {url}")
		
		try:
			r = requests.get(url, timeout=10, verify=False)
			if r.status_code != 200:
				Domoticz.Error(f"Failed to load devices: HTTP {r.status_code}")
				return 0
			
			data = r.json()
			if data.get("status") != "OK":
				Domoticz.Error("API returned not OK status")
				return 0
			
			self.idx_cache.clear()
			for dev in data.get("result", []):
				desc = dev.get("Description", "").strip()
				if not desc:
					continue
			
				try:
					desc_json = json.loads(desc)
					topic = desc_json.get("Topic")
					#Domoticz.Log(f"topic = {topic}")
					device = desc_json.get("Device")
					#Domoticz.Log(f"device = {device}")
					
					if device == "Switch3" and topic == module_topic:
						return int(dev["idx"])
					
				except json.JSONDecodeError:
					continue
				
		except Exception as e:
			Domoticz.Error(f"Error loading devices: {e}")
			return 0
		return 0
		
			
	def onStop(self):
		Domoticz.Log("Plugin stopping...")
		# if self.mqttClient:
			# self.mqttClient.loop_stop()
			# self.mqttClient.disconnect()
	
	def onMQTTConnect(self, client, userdata, flags, rc):
		if rc == 0:
			Domoticz.Log("Connected to MQTT broker")
			client.subscribe("tele/#")
			client.subscribe("stat/#")
		else:
			Domoticz.Error(f"MQTT connect failed (code {rc})")
	
	def onMQTTDisconnect(self, client, userdata, rc):
		Domoticz.Log(f"MQTT disconnected (code {rc})")
	
	def onMQTTMessage(self, client, userdata, msg):
		topic = msg.topic
		try:
			payload_str = msg.payload.decode("utf-8").strip()
		except:
			return
		
		if not payload_str or topic.endswith(("/LWT", "/INFO1", "/INFO2", "/INFO3")):
			return
		
		topic_parts = topic.split('/')

		device_topic = topic_parts[1]
		device_topic_list = device_topic.split('_')
		module_id = device_topic_list[1]
		
		try:
			payload_json = json.loads(payload_str)
		except json.JSONDecodeError:
			return
			
		try:
			for key, value in payload_json.items():
				#Domoticz.Log(f"key = {key}, val = {value} module_id = {module_id}")
				if key.startswith("Switch3") and str(value).upper() in ["ON", "OFF"]:
					state = str(value).upper()
					target_key = f"cmnd/{device_topic}/{key}"
					#idx = self.idx_cache.get(target_key)
					idx = int(self.alarm_switch[module_id])
					if idx:
						Domoticz.Log(f"Updating {target_key} → IDX {idx} = {state}")
						self.send_update_to_domoticz(idx, state)
					else:
						#Domoticz.Log(f"No cached IDX for {target_key}")
						pass
					self.switchSlaveAlarmToMaster()
						
				if key.startswith("Switch3") and str(value).upper() == "{'ACTION': 'TOGGLE'}":
					state = str(value).upper()
					target_key = f"cmnd/{device_topic}/{key}"
					#idx = self.idx_cache.get(target_key)
					idx = int(self.alarm_switch[module_id])
					if idx:
						Domoticz.Log(f"Updating toggle {target_key} → IDX {idx} = {state}")
						self.send_update_to_domoticz(idx, state)
					else:
						#Domoticz.Log(f"No cached IDX for {target_key}")
						pass	
					self.switchSlaveAlarmToMaster()
		except Exception as e:
			Domoticz.Error(f"Error processing message: {e}")
	
	def send_update_to_domoticz(self, idx, state):		 
	
		DzAddress = Parameters['Address']		
		
		url = f"{DzAddress}/json.htm?type=command&param=switchlight&idx={idx}&switchcmd={'On' if state == 'ON' else 'Off' if state == 'OFF' else 'Toggle'}"
		
		Domoticz.Log(f"send_update_to_domoticz url = {url}")
		
		try:
			r = requests.get(url, timeout=10, verify=False)
			if r.status_code == 200:
				Domoticz.Log(f"Successfully updated IDX {idx} → {state}")
			else:
				Domoticz.Error(f"API error {r.status_code}: {r.text}")
		except Exception as e:
			Domoticz.Error(f"Update failed: {e}")
			
	def changeSwitchState(self, idx, state):		 
	
		DzAddress = Parameters['Address']		
		
		url = f"{DzAddress}/json.htm?type=command&param=switchlight&idx={idx}&switchcmd={state}"
		
		#Domoticz.Log(f"changeSwitchState url = {url}")
		
		try:
			r = requests.get(url, timeout=10, verify=False)
			if r.status_code == 200:
				Domoticz.Log(f"Successfully updated IDX {idx} → {state}")
			else:
				Domoticz.Error(f"API error {r.status_code}: {r.text}")
		except Exception as e:
			Domoticz.Error(f"Update failed: {e}")
						
	def get_virtual_devices_hardware_idx(self) -> int:

		dz_url = Parameters["Address"]
		api_url = f"{dz_url}/json.htm?type=command&param=gethardware"

		try:
			r = requests.get(api_url, timeout=10, verify=False)
			r.raise_for_status()

			data = r.json()

			if data.get("status") != "OK":
				Domoticz.Error("gethardware: status != OK")
				return -1

			for hw in data.get("result", []):
				if hw.get("Name") == "VirtualDevices":
					idx = int(hw.get("idx", 0))
					Domoticz.Log(f"Найден VirtualDevices → idx = {idx}")
					return idx

			Domoticz.Log("Hardware с именем 'VirtualDevices' не найден")
			return -1

		except requests.exceptions.RequestException as e:
			Domoticz.Error(f"Ошибка запроса gethardware: {e}")
			return -1
		except (ValueError, TypeError, json.JSONDecodeError) as e:
			Domoticz.Error(f"Ошибка обработки ответа gethardware: {e}")
			return -1	
			
	def get_device_json(self, idx: int) -> dict | None:

		base_url = Parameters["Address"]
		api_url = f"{base_url}/json.htm?type=command&param=getdevices&rid={idx}"

		try:
			response = requests.get(api_url, timeout=10, verify=False)
			response.raise_for_status()

			data = response.json()

			if data.get("status") != "OK":
				Domoticz.Error(f"getdevices rid={idx} return status: {data.get('status')}")
				return None

			result = data.get("result", [])
			if not result:
				Domoticz.Log(f"Device idx={idx} does not found")
				return None

			device = result[0]
			#Domoticz.Log(f"response with params idx={idx}: {device.get('Name')}")

			return device

		except requests.exceptions.RequestException as re:
			Domoticz.Error(f"RequestException idx={idx}: {re}")
			return None
		except (ValueError, TypeError, json.JSONDecodeError) as je:
			Domoticz.Error(f"JSON-Exception for idx={idx}: {je}")
			return None
		except Exception as e:
			Domoticz.Error(f"Unknown error idx={idx}: {e}")
			return None
			
	def get_device_param(self, idx: int, param_name: str, default=None):
		device = self.get_device_json(idx)
		
		if device is None:
			Domoticz.Error(f"get_device_param: device idx={idx} does not response")
			return default
			
		value = device.get(param_name)
		
		if value is None:
			Domoticz.Log(f"field '{param_name}' does not exist idx={idx}")
			return default
			
		
		return value			
			
	def find_alarmdevice_idx(self, module_id: str, command_id: str) -> int:

		base_url = Parameters["Address"]
		api_url = f"{base_url}/json.htm?type=command&param=getdevices&filter=light&used=true&order=Name"
		
		try:
			response = requests.get(api_url, timeout=10, verify=False)
			response.raise_for_status()

			data = response.json()
			#Domoticz.Log(f"FAI idx:{data.get("idx")} status:{data.get("status")}")

			if data.get("status") != "OK":
				Domoticz.Error("getdevices: status != OK")
				return -1

			for dev in data.get("result", []):
				desc = dev.get("Description", "").strip()
				if not desc:
					continue

				try:
					desc_json = json.loads(desc)
					topic = desc_json.get("Topic", "")
					command = desc_json.get("Command", "")
					
					topic_find = f"/tasmota_{module_id}"
					#Domoticz.Log(f"FAI topic:{topic} command:{command}")
					#Domoticz.Log(f"FAI topic:{topic_find} command:{command_id} {topic.find(topic_find)}")

					if topic.find(topic_find) > 0 and command == command_id:
						idx = int(dev["idx"])
						#Domoticz.Log(f"FAI found module={module_id}, command={command_id} → idx={idx}")
						return idx
				except json.JSONDecodeError:
					Domoticz.Debug(f"FAI invalid JSON in Description  idx={dev.get('idx')}")
					continue
				except ValueError:
					Domoticz.Error(f"FAI invalid idx for device: {dev.get('Name')}")
					continue

			#Domoticz.Log(f"FAI	 device ={module_id}, command={command_id} not found")
			return -1

		except requests.exceptions.RequestException as re:
			Domoticz.Error(f"Request error getdevices: {re}")
			return -1
		except Exception as e:
			Domoticz.Error(f"Unknown error in find_device_idx: {e}")
			return -1
			
	def send_notification(self, subject: str, body: str) -> bool:
		if not subject.strip() or not body.strip():
			Domoticz.Error("send_notification: subject or body are empty")
			return False
			
		base_url = Parameters["Address"]

		url = (
			f"{base_url}/json.htm?"
			f"type=command&"
			f"param=sendnotification&"
			f"subject={subject}&"
			f"body={body}"
		)

		try:
			r = requests.get(url, timeout=8, verify=False)
			
			if r.status_code != 200:
				Domoticz.Error(f"sendnotification: HTTP {r.status_code}")
				return False

			data = r.json()
			
			if data.get("status") == "OK":
				Domoticz.Log(f"The notification was sended: {subject}")
				return True
			else:
				Domoticz.Error(f"send notification error: status = {data.get('status')}")
				return False

		except requests.exceptions.RequestException as e:
			Domoticz.Error(f"Error on notification: {e}")
			return False
		except Exception as e:
			Domoticz.Error(f"Unknown error send_notification: {e}")
			return False			
			
	def get_public_ip(self, timeout: int = 5) -> str:
		urls = [
			("https://api.ipify.org",			lambda r: r.text.strip()),
			("https://api64.ipify.org",			lambda r: r.text.strip()),	# может вернуть IPv6
			("https://ifconfig.io/ip",			lambda r: r.text.strip()),
			("https://ipecho.net/plain",		lambda r: r.text.strip()),
			("https://icanhazip.com",			lambda r: r.text.strip()),
			("https://checkip.amazonaws.com",	lambda r: r.text.strip()),
		]

		for url, extractor in urls:
			try:
				r = requests.get(url, timeout=timeout, allow_redirects=True)
				if r.status_code == 200:
					ip = extractor(r).strip()
					# простая проверка IPv4
					parts = ip.split(".")
					if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
						return ip
			except:
				continue

		return ""
		
	def refresh_public_ip(self):
		try:
			self.public_ip = self.get_public_ip()
			Domoticz.Log(f"Public IP:{self.public_ip}")
		except Exception as e:
			Domoticz.Error(f"refresh_public_ip():E:{e}")
			
			
	def check_alarm_refs(self):
		for m_idx in self.alarm_master_refs:
			for s_idx in self.alarm_master_refs[m_idx]:
				try:
					stat_str = self.get_device_param(m_idx, "Status")
					Domoticz.Log(f"check_alarm_refs() {m_idx}->{s_idx} {stat_str}")
					self.changeSwitchState(s_idx, stat_str)
				except Exception as e:
					Domoticz.Error(f"check_alarm_refs():E:{e}")
					
	def switchSlaveAlarmToMaster(self):
		try:
			#Domoticz.Log(f"sSATM: self.alarm_master : {self.alarm_master}")
			if self.alarm_master != {}:
				stat_str = self.get_device_param(self.alarm_master_switch1_idx, "Status")
				#Domoticz.Log(f"sSATM: self.alarm_switch = {self.alarm_switch} {stat_str}")
				if stat_str == "On":
					for s_mid in self.alarm_switch:
						#Domoticz.Log(f"sSATM: s_mid = {s_mid}")
						s_idx = self.alarm_switch[s_mid]
						#Domoticz.Log(f"sSATM: s_idx = {s_idx}")
						s_s3state = self.get_device_param(s_idx, "Status")
						if s_s3state == 'On':
							Domoticz.Log(f"switchSlaveAlarmToMaster()switch3 {s_idx} is On !!!")
							self.changeSwitchState(self.alarm_master_switch2_idx, s_s3state) 
							self.send_notification("ALARM:", f'Sirena: https://{self.public_ip}/')
		except Exception as e:
			Domoticz.Error(f"switchSlaveAlarmToMaster():E:{e}")
			
	def onHeartbeat(self):
		# Обновляем кэш раз в 10 минут (60 heartbeats = ~10 мин)
		if not hasattr(self, "_heartbeat_count"):
			self._heartbeat_count = 0
		self._heartbeat_count += 1
		
		if not hasattr(self, "_heartbeat_alarmcount"):
			self._heartbeat_alarmcount = 0
		self._heartbeat_alarmcount += 1
		
		if not hasattr(self, "_heartbeat_pipcount"):
			self._heartbeat_pipcount = 0
		self._heartbeat_pipcount += 1
		
		
		#if self._heartbeat_count >= 60:
		#	 self._heartbeat_count = 0
		#	 self.load_devices_cache()
		
		if self._heartbeat_count >= 3:
			self._heartbeat_count = 0
			self.check_alarm_refs()
			#self.switchSlaveAlarmToMaster()
			
		if self._heartbeat_alarmcount >= 1:
			self._heartbeat_alarmcount = 0
			self.switchSlaveAlarmToMaster()
			
		if self._heartbeat_pipcount > 3600:
			self._heartbeat_pipcount = 0
			self.refresh_public_ip()
	
global _plugin
#_plugin = BasePlugin()
_plugin = Plugin()
	
def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onConnect(Connection, Status, Description): pass
def onMessage(Connection, Data): pass
def onCommand(Unit, Command, Level, Color): pass
def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile): pass
def onDisconnect(Connection): pass
def onHeartbeat(): _plugin.onHeartbeat()