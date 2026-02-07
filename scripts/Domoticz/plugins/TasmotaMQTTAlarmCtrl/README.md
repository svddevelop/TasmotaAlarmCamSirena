# Domoticz Plugin

## Settings

![Settings in Domoticz](domoticz_AlarmSirenaSettings.jpg)

**Status:** In development.

In the "Domoticz IP" field, you need to specify the http connection to the Domoticz server.  
If the service is running on the current computer, use:  
`http://127.0.0.1`

If you need an authenticated connection, enter everything in one line:  
`http://admin:domoticz@127.0.0.1`

However, it is much simpler to use the first option and configure Domoticz to trust the local network address `127.*` in the security settings.

Next, enter the connection parameters for the MQTT service. If authentication is required, specify the username and password.

The most important parameter is **Alarm settings**.

In this text field, you need to enter the identifiers that can be found in the information section of each specific Tasmota module:  

![Tasmota-Info](tasmota-device-info.jpg)  
*(The identifier is highlighted in yellow in the image.)*

Example input:  
`alarmmodules=94F93D,502044;alarmmaster=94F93D;`

Where:  
- `alarmmodules` — list of **all** modules used in the network  
- `alarmmaster` — specified only if you need centralized control from one particular module

After making all changes, save the configuration and restart the Domoticz service so that the changes take effect.

After the restart, within some time the plugin will automatically detect the required devices and add them to the list of switches.

The configuration of an individual module includes three switches:

![tasmota-module-configuration](tasmota-module-conf.jpg)

**Relay1** — set when the system should monitor the perimeter breach sensor.  
**Relay2** — set when the siren needs to be activated.  
**Switch3** — displays the current state of the sensor.

### What need to set for switches

![Domoticz-switches](tasmota-switches.jpg)

It will be more visually clear if you change the icon of the switches responsible for siren activation and monitoring activation.

#### How it works:

- If **Relay1** is not active, all signals from the sensor are ignored.  
- As soon as **Relay1** is activated and a change occurs on sensor **Switch3**, **Relay2** turns on and the siren starts emitting intermittent signals.  
- To turn off the siren, first deactivate **Relay1**, then **Relay2**.

If one module is defined as **master**, this means that when **Relay1** and **Relay2** are toggled on the master module, within a short time (within 20 seconds) all other modules will automatically take the same state for these switches.

If the perimeter sensor triggers on any of the modules, the siren will automatically activate on the device that is set as **master**.