# Domoticz Plugin

## Settings

![Settings in Domoticz](domoticz_AlarmSirenaSettings.jpg)

Stady: Develop.

#### How it works:
Every virtual device in the Domoticz how connected to TasmotaAlarmSirena, have the follows JSONin the Description:

`
{
  "Topic": "cmnd/tasmota_94F93D",
  "Command": "POWER1",
  "Device": "Schalter",
  "Type": "1",
  "Name": "AlarmCam2Ctrl 1",
  "Module": "Generic",
  "Version": "15.2.0(release-tasmota)"
}
` 
But the Domoticz does not registered the switch3 of real electronic TasmotaAlarmSirena. It need to do manually:

- append new virtual device;
- write the Description with follows JSON:
`{
  "Topic": "cmnd/tasmota_94F93D",
  "Device": "Switch3",
  "Type": "2",
  "Name": "AlarmCam2"
}`
- change the picture of the virtual switch.

After it will be any MQTT check the information from the switch3 for 'ON', 'OFF' and 'TOGGLE' and change it on the dashboard.


### What will be changed in the future

* add button "append TasmotaAlarmSirenaSwitch3" with autoatically filling of the Desctiption with JSON;
* as parameter will be device numeration.

