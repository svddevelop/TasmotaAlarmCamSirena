"""
<plugin
    key="tMQTTalarm"
    name="Tasmota MQTT Alarm Integration"
    author="S.Pfaffenrot"
    version="1.1.0"
    externallink="https://github.com/svddevelop/TasmotaAlarmCamSirena">
    <description>
        Tasmota MQTT Integration Plugin<br/>
        Automatic scanned the IDX from JSONin Description and refersh the status in Tasmota tele/SENSOR.
    </description>
    <params>
        <!-- Domoticz API -->
        <param field="Address" label="Domoticz IP" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Domoticz Port" width="80px" required="true" default="8080"/>
        <param field="Username" label="Domoticz Username" width="200px" required="false"/>
        <param field="Password" label="Domoticz Password" width="200px" required="false" password="true"/>
        
        <!-- MQTT Broker -->
        <param field="Mode1" label="MQTT Server" width="200px" required="true" default="127.0.0.1"/>
        <param field="Mode2" label="MQTT Port" width="80px" required="true" default="1883"/>
        <param field="Mode3" label="MQTT Username" width="200px" required="false"/>
        <param field="Mode4" label="MQTT Password" width="200px" required="false" password="true"/>
        
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

import Domoticz
import json
import paho.mqtt.client as mqtt
import requests

class BasePlugin:
    def __init__(self):
        self.mqttClient = None
        self.idx_cache = {}  # ключ: "cmnd/tasmota_XXXXXX/SwitchY" → IDX
        self.debug = False

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            self.debug = True
            Domoticz.Debugging(1)

        #Domoticz.Log("Plugin::onStart: Parameters: {}".format(repr(Parameters)))
        #Domoticz.Log("Tasmota MQTT Alarm Integration starting...")
        #Domoticz.Log("MqttUsername:" + Parameters["MqttUsername"].strip() )
        #Domoticz.Log("MqttPassword:" + Parameters["MqttPassword"].strip() )
        #Domoticz.Log("MqttAddress:" + Parameters["MqttAddress"].strip() )
        #Domoticz.Log("MqttPort:" + Parameters["MqttPort"].strip() )
        #Domoticz.Log("DzPort:" + Parameters["DzPort"].strip() )
        #Domoticz.Log("DzAddress:" + Parameters["DzAddress"].strip() )

        # Загружаем устройства и строим кэш IDX
        self.load_devices_cache()

        # Подключаемся к MQTT
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.onMQTTConnect
        self.mqttClient.on_disconnect = self.onMQTTDisconnect
        self.mqttClient.on_message = self.onMQTTMessage

        if Parameters["Mode3"].strip():
            self.mqttClient.username_pw_set(Parameters["Mode3"], Parameters["Mode4"])

        try:
            MqttAddress = 'localhost'
            MqttPort = 1883
            MqttAddress = Parameters["Mode1"].strip()
            MqttPort = int(Parameters["Mode2"])
            self.mqttClient.connect(MqttAddress, MqttPort, 60)
            self.mqttClient.loop_start()
            Domoticz.Log("MQTT connection initiated")
        except Exception as e:
            Domoticz.Error(f"MQTT connection failed: {e}")

    def load_devices_cache(self):
        DzAddress = '127.0.0.1'
        DzPort = '8080'
        DzAddress = Parameters['Address']
        DzUsername = Parameters["Username"]
        DzPassword = Parameters["Password"]
        DzPort = Parameters["Port"]
        protocol = "https" if DzPort in ["443", "8443"] else "http"
        url = f"{protocol}://{DzAddress}:{DzPort}/json.htm?type=command&param=getdevices&filter=light&used=true&order=Name"
        

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
                    device = desc_json.get("Device")
                    if topic and device and dev.get("idx"):
                        key = f"{topic}/{device}"
                        self.idx_cache[key] = int(dev["idx"])
                        Domoticz.Log(f"Cached: {key} → IDX {dev['idx']} ({dev['Name']})")
                except json.JSONDecodeError:
                    continue

            Domoticz.Log(f"Device cache loaded: {len(self.idx_cache)} entries")

        except Exception as e:
            Domoticz.Error(f"Error loading devices: {e}")

    def onStop(self):
        Domoticz.Log("Plugin stopping...")
        if self.mqttClient:
            self.mqttClient.loop_stop()
            self.mqttClient.disconnect()

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
        #if len(topic_parts) < 3 or not topic.endswith("/SENSOR"):
        #    return
        #if len(topic_parts) < 3 or (not topic.endswith("/SENSOR")) or (not topic.endswith("/RESULT")):
        #    Domoticz.Log("topic="+topic)
        #    return
        #Domoticz.Log("point159")
        device_topic = topic_parts[1]

        try:
            payload_json = json.loads(payload_str)
        except json.JSONDecodeError:
            return

        try:
            for key, value in payload_json.items():
                #Domoticz.Log(f"key = {key}, val = {value}")
                if key.startswith("Switch3") and str(value).upper() in ["ON", "OFF"]:
                    state = str(value).upper()
                    target_key = f"cmnd/{device_topic}/{key}"
                    idx = self.idx_cache.get(target_key)
                    if idx:
                        Domoticz.Log(f"Updating {target_key} → IDX {idx} = {state}")
                        self.send_update_to_domoticz(idx, state)
                    else:
                        pass  # или раскомментировать лог ниже
                        #Domoticz.Log(f"No cached IDX for {target_key}")
                        
                if key.startswith("Switch3") and str(value).upper() == "{'ACTION': 'TOGGLE'}":
                    state = str(value).upper()
                    target_key = f"cmnd/{device_topic}/{key}"
                    idx = self.idx_cache.get(target_key)
                    if idx:
                        Domoticz.Log(f"Updating toggle {target_key} → IDX {idx} = {state}")
                        self.send_update_to_domoticz(idx, state)
                    else:
                        pass  # или раскомментировать лог ниже
                        #Domoticz.Log(f"No cached IDX for {target_key}")
        except Exception as e:
            Domoticz.Error(f"Error processing message: {e}")

    def send_update_to_domoticz(self, idx, state):       
        DzPort = '8080'
        DzPort = Parameters["Port"] 
        DzAddress = '127.0.0.1'
        DzAddress = Parameters['Address']
        DzUser = Parameters["Password"]
        DzPasswd = Parameters["Port"]
        
        protocol = "https" if DzPort in ["443", "8443"] else "http"
        url = f"{protocol}://{DzAddress}:{DzPort}/json.htm?type=command&param=switchlight&idx={idx}&switchcmd={'On' if state == 'ON' else 'Off' if state == 'OFF' else 'Toggle'}"
        
        #Domoticz.Log(f"send_update_to_domoticz url = {url}")

        try:
            r = requests.get(url, timeout=10, verify=False)
            if r.status_code == 200:
                Domoticz.Log(f"Successfully updated IDX {idx} → {state}")
            else:
                Domoticz.Error(f"API error {r.status_code}: {r.text}")
        except Exception as e:
            Domoticz.Error(f"Update failed: {e}")

    # Можно обновлять кэш периодически
    def onHeartbeat(self):
        # Обновляем кэш раз в 10 минут (60 heartbeats = ~10 мин)
        if not hasattr(self, "_heartbeat_count"):
            self._heartbeat_count = 0
        self._heartbeat_count += 1
        #if self._heartbeat_count >= 60:
        #    self._heartbeat_count = 0
        #    self.load_devices_cache()

global _plugin
_plugin = BasePlugin()

def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onConnect(Connection, Status, Description): pass
def onMessage(Connection, Data): pass
def onCommand(Unit, Command, Level, Color): pass
def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile): pass
def onDisconnect(Connection): pass
def onHeartbeat(): _plugin.onHeartbeat()