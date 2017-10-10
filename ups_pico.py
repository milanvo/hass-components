"""
Component to interface with UPS PIco (by Pimodules).

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/
"""
import asyncio
import logging

# import voluptuous as vol

from homeassistant.helpers.entity import Entity, ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval

REQUIREMENTS = ['smbus2==0.2.0']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'ups_pico'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

SENSOR_TYPES = {
    'voltBat': ['BAT Voltage', 'V', 'battery'],
    'voltRpi': ['RPi Voltage', 'V', 'power-plug'],
    'tempNtc1': ['NTC1 Temperature', '°C', 'thermometer'],
    'pwrMode': ['Powering Mode', None, 'power'],
}
SWITCH_TYPES = {
    'ledOrange': ['Orange LED', 'led-off'],
    'ledGreen': ['Green LED', 'led-off'],
    'ledBlue': ['Blue LED', 'led-off'],
    'ledEnable': ['Enabled LEDs', 'led-off']
}


@asyncio.coroutine
def async_setup(hass, config):
    """Set up the UPS PIco component."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    entities = []
    ups_pico = UpsPico()
    ups_pico.getData()

    for object_id, cfg in SENSOR_TYPES.items():
        name = cfg[0]
        unit = cfg[1]
        icon = 'mdi:' + cfg[2]

        entities.append(UpsPicoSensor(ups_pico, object_id, name, unit, icon))

    for object_id, cfg in SWITCH_TYPES.items():
        name = cfg[0]
        icon = 'mdi:' + cfg[1]

        entities.append(UpsPicoSwitch(ups_pico, object_id, name, icon))

    if not entities:
        return False

    async_track_time_interval(hass, ups_pico.getData, component.scan_interval)

    yield from component.async_add_entities(entities)
    return True


class UpsPicoSensor(Entity):
    """Representation of UPS PIco sensor"""

    def __init__(self, ups_pico, object_id, name, unit, icon):
        """Initialize the sensor"""
        self.ups_pico = ups_pico
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._object_id = object_id
        self._name = name
        self._state = None
        self._unit_of_measurement = unit
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    def update(self):
        """Update sensor state."""
        self._state = self.ups_pico.picoData[self._object_id]

class UpsPicoSwitch(ToggleEntity):
    """Representation of UPS PIco switch"""

    def __init__(self, ups_pico, object_id, name, icon):
        """Initialize the switch."""
        self.ups_pico = ups_pico
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._object_id = object_id
        self._name = name
        self._state = None
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self.ups_pico.ledOn(self._object_id)
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.ups_pico.ledOff(self._object_id)
        self._state = False
        self.schedule_update_ha_state()

    def update(self):
        """Update switch state."""
        self._state = self.ups_pico.picoData[self._object_id]

class UpsPico(object):
    """Class for UPS PIco i2c interface"""

    def __init__(self):
        import smbus2

        self.picoReg = dict()
        self.picoData = dict()
        self.i2c = smbus2.SMBus(1)
        self.regDict = {
            "ledOrange": 0x09,
            "ledGreen": 0x0a,
            "ledBlue": 0x0b,
            "ledEnable": 0x15,
        }
        return

    def _tryGetData(self):
        try:
            reg = self.i2c.read_i2c_block_data(0x69, 0, 0x1d)
            reg += [0xff, 0xff, 0xff]
            reg += (self.i2c.read_i2c_block_data(0x69, 0x20, 7))
            self.picoReg[0x69] = reg

            reg = self.i2c.read_i2c_block_data(0x6b, 0, 0x16)
            self.picoReg[0x6b] = reg

        except Exception as e:
            _LOGGER.error('Except class PicoPlugin _tryGetData(): ' + str(e))
            return False

        return True

    def setData(self, device, data):
        addr = 0x6b
        if device in self.regDict:
            reg = self.regDict[device]
            try:
                self.i2c.write_byte_data(addr, reg, data)
                return True
            except Exception as e:
                _LOGGER.error('Except class PicoPlugin setData(): ' + str(e))
        else:
            _LOGGER.error('Error class PicoPlugin setData(): Unknown device',
                          device)

        return False

    def ledOn(self, device):
        return self.setData(device, 1)

    def ledOff(self, device):
        return self.setData(device, 0)

    def getData(self):
        result = self._tryGetData()

        if not result:
            return False

        # *** 0x69 registers
        data = self.picoReg[0x69]

        # 0x69 0x00 Powering mode
        reg_word = data[0x00]
        if reg_word == 1:
            self.picoData["pwrMode"] = "RPi powered"
        elif reg_word == 2:
            self.picoData["pwrMode"] = "UPS powered"

        # 0x69 0x08 BAT voltage
        reg_word = int.from_bytes(data[0x08:0x0a], byteorder="little")
        reg_hex = format(reg_word, "02x")
        reg_volt = float(reg_hex) / 100
        self.picoData["voltBat"] = reg_volt

        # 0x69 0x0a RPi voltage
        reg_word = int.from_bytes(data[0x0a:0x0c], byteorder="little")
        reg_hex = format(reg_word, "02x")
        reg_volt = float(reg_hex) / 100
        self.picoData["voltRpi"] = reg_volt

        # 0x69 0x1b NTC1 temperature
        reg_word = data[0x1b]
        reg_hex = format(reg_word, "02x")
        self.picoData["tempNtc1"] = reg_hex

        # 0x69 0x24 PCB version
        reg_word = data[0x24]
        reg_chr = chr(reg_word)
        self.picoData["verPCB"] = reg_chr

        # 0x69 0x25 Bootloader version
        reg_word = data[0x25]
        reg_chr = chr(reg_word)
        self.picoData["verBoot"] = reg_chr

        # 0x69 0x26 FW version
        reg_word = data[0x26]
        reg_hex = format(reg_word, "02x")
        self.picoData["verFW"] = reg_hex

        # *** 0x6b registers
        data = self.picoReg[0x6b]

        # 0x6b 0x01 Bat Powering time
        reg_word = data[0x01]
        if reg_word == 0xff:
            self.picoData["pwrRunTime"] = "disabled"
        else:
            self.picoData["pwrRunTime"] = 1 + reg_word

        # 0x6b 0x09, 0x0a, 0x0b User LEDs Orange, Green, Blue
        self.picoData["ledOrange"] = data[0x09]
        self.picoData["ledGreen"] = data[0x0a]
        self.picoData["ledBlue"] = data[0x0b]

        # 0x6b 0x15 Enable LEDs
        self.picoData["ledEnable"] = data[0x15]

        return True

    def getTest(self):
        """Testing code"""

        reg1 = self.i2c.read_i2c_block_data(0x69, 0, 0x1d)
        print("reg 0x69 0-0x1c:", reg1, "\nlength:", len(reg1))
        reg2 = self.i2c.read_i2c_block_data(0x69, 0x20, 7)
        print("reg 0x69 0x20-0x26::", reg2, "\nlength:", len(reg2))

        data = self.i2c.read_word_data(0x69, 0x08)
        print("\n")
        print("BAT Voltage")
        print("word 0x69 0x08:", data)
        print("word 0x69 0x08 Format:", format(data, "02x"))
        print("Volts:", str(float(format(data, "02x")) / 100))

        data = self.i2c.read_word_data(0x69, 0x0a)
        print("\n")
        print("RPi Voltage")
        print("word 0x69 0x0a:", data)
        print("word 0x69 0x0a Format:", format(data, "02x"))
        print("Volts:", str(float(format(data, "02x")) / 100))

        result = self.getData()

        if not result:
            print("Failed getData")
            return

        print()
        print("picoReg 0x69 0-0x26:", self.picoReg[0x69], "\nlength:", len(self.picoReg[0x69]))
        print("picoReg 0x6b 0-0x15:", self.picoReg[0x6b], "\nlength:", len(self.picoReg[0x6b]))
        print()
        #print("BAT Voltage:", str(int.from_bytes(data[8:10], byteorder="little")), str(float(format(int.from_bytes(data[8:10], byteorder="little"), "02x"))/100))
 
        print("BAT Voltage (V): " + str(self.picoData["voltBat"]))
        print("RPi Voltage (V): " + str(self.picoData["voltRpi"]))
        print("NTC1 Temperature (deg. C): " + str(self.picoData["tempNtc1"]))
        print("Powering mode: " + self.picoData["pwrMode"])
        print("Bat Powering running time (min): " + str(self.picoData["pwrRunTime"]))
        print("User LED Orange: " + str(self.picoData["ledOrange"]))
        print("User LED Green: " + str(self.picoData["ledGreen"]))
        print("User LED Blue: " + str(self.picoData["ledBlue"]))
        print("Enable LEDs: " + str(self.picoData["ledEnable"]))
        print("-"*20)
        print("PCB version: " + self.picoData["verPCB"])
        print("Bootloader version: " + self.picoData["verBoot"])
        print("FW version: " + str(self.picoData["verFW"]))


deviceDict = {
        1: {
            "Name": "BAT Voltage",
            "Unit": 1,
            "TypeName": "Voltage",
            "picoName": "voltBat",
        },
        2: {
            "Name": "RPi Voltage",
            "Unit": 2,
            "TypeName": "Voltage",
            "picoName": "voltRpi",
        },
        3: {
            "Name": "NTC1 Temperature",
            "Unit": 3,
            "TypeName": "Temperature",
            "picoName": "tempNtc1",
        },
        4: {
            "Name": "Powering Mode",
            "Unit": 4,
            "TypeName": "Text",
            "picoName": "pwrMode",
        },
        5: {
            "Name": "Orange LED",
            "Unit": 5,
            "TypeName": "Switch",
            "picoName": "ledOrange",
        },
        6: {
            "Name": "Green LED",
            "Unit": 6,
            "TypeName": "Switch",
            "picoName": "ledGreen",
        },
        7: {
            "Name": "Blue LED",
            "Unit": 7,
            "TypeName": "Switch",
            "picoName": "ledBlue",
        },
        8: {
            "Name": "Enabled LEDs",
            "Unit": 8,
            "TypeName": "Switch",
            "picoName": "ledEnable",
        },
        99: {
            "Name": "Test",
            "Unit": 99,
            "TypeName": "Switch",
            "picoName": "Test",
        },
}

"""
    result = _pico.getData()
    #Domoticz.Log("reg 0x69 0-0x26:" + str(data) + "\nlength:" + str(len(data)))
    Domoticz.Log("PCB version: " + _pico.picoData["verPCB"])
    Domoticz.Log("Bootloader version: " + _pico.picoData["verBoot"])
    Domoticz.Log("FW version: " + str(_pico.picoData["verFW"]))
    Domoticz.Log("Bat Powering running time (min): " + str(_pico.picoData["pwrRunTime"]))
    Domoticz.Debug("-" * 20)
    Domoticz.Debug("BAT Voltage: " + str(_pico.picoData["voltBat"]))
    Domoticz.Debug("RPi Voltage: " + str(_pico.picoData["voltRpi"]))
    Domoticz.Debug("NTC1 Temperature: " + str(_pico.picoData["tempNtc1"]))
    Domoticz.Debug("Powering Mode: " + _pico.picoData["pwrMode"])
    Domoticz.Debug("User LED Orange: " + str(_pico.picoData["ledOrange"]))
    Domoticz.Debug("User LED Green: " + str(_pico.picoData["ledGreen"]))
    Domoticz.Debug("User LED Blue: " + str(_pico.picoData["ledBlue"]))
    Domoticz.Debug("Enable LEDs: " + str(_pico.picoData["ledEnable"]))

    if result:
        UpdateDevice(1, 0, str(_pico.picoData["voltBat"]), updEvery=True)
        UpdateDevice(2, 0, str(_pico.picoData["voltRpi"]), updEvery=True)
        UpdateDevice(3, 0, str(_pico.picoData["tempNtc1"]), updEvery=True)
        UpdateDevice(4, 0, _pico.picoData["pwrMode"])
        UpdateDevice(5, _pico.picoData["ledOrange"], "0")
        UpdateDevice(6, _pico.picoData["ledGreen"], "0")
        UpdateDevice(7, _pico.picoData["ledBlue"], "0")
        UpdateDevice(8, _pico.picoData["ledEnable"], "0")

    #DumpConfigToLog()

def onStop():
    Domoticz.Log("Plugin is stopping.")

def onCommand(Unit, Command, Level, Hue):
    global _pico

    if (Command.upper() == 'ON'):
        status = _pico.ledOn(deviceDict[Unit]["picoName"])
        nValue = 1
        sValue = "0"
    else:
        status = _pico.ledOff(deviceDict[Unit]["picoName"])
        nValue = 0
        sValue = "0"
    
    if status:
        UpdateDevice(Unit, nValue, sValue)

def onHeartbeat():
    global _pico

    result = _pico.getData()

    if result:
        UpdateDevice(1, 0, str(_pico.picoData["voltBat"]), updEvery=True)
        UpdateDevice(2, 0, str(_pico.picoData["voltRpi"]), updEvery=True)
        UpdateDevice(3, 0, str(_pico.picoData["tempNtc1"]), updEvery=True)
        UpdateDevice(4, 0, _pico.picoData["pwrMode"])
        UpdateDevice(5, _pico.picoData["ledOrange"], "0")
        UpdateDevice(6, _pico.picoData["ledGreen"], "0")
        UpdateDevice(7, _pico.picoData["ledBlue"], "0")
        UpdateDevice(8, _pico.picoData["ledEnable"], "0")

def UpdateDevice(Unit, nValue, sValue, updEvery=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue, str(sValue))
            #Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
        elif updEvery:
            # Update device even not changed every X minutes - for Temp and Volt values
            updMinutes = 15
            Domoticz.Debug("LastUpdate: '" + Devices[Unit].LastUpdate + "' ("+Devices[Unit].Name+")")
            #devUpdate = datetime.strptime("2017-06-22 18:24:21", "%Y-%m-%d %H:%M:%S")
            #devUpdate = datetime.strptime(Devices[Unit].LastUpdate, "%Y-%m-%d %H:%M:%S")
            devUpdate = datetime(*(time.strptime(Devices[Unit].LastUpdate, "%Y-%m-%d %H:%M:%S")[0:6]))
            devBefore = datetime.now() - devUpdate
            if (devBefore > timedelta(minutes=updMinutes)):
                Domoticz.Debug("Updated before: " + str(devBefore) + " ("+Devices[Unit].Name+")")
                Devices[Unit].Update(nValue, str(sValue))
    return

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def main():
    _pico.getTest()

if __name__ == '__main__':
    main()
"""