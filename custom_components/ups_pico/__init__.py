"""
Component to interface with UPS PIco (by Pimodules).

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/
"""
# NO ASYNC import asyncio
import logging

# import voluptuous as vol

#from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import track_time_interval
# NO ASYNC from homeassistant.helpers.event import async_track_time_interval

from homeassistant.components.sensor import (               
    SensorDeviceClass,                                            
    SensorStateClass,                                             
)
from homeassistant.const import UnitOfTemperature

REQUIREMENTS = ['smbus2==0.2.0']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'ups_pico'
SENSOR_ID_FORMAT = DOMAIN + '.{}'
SENSOR_NAME_FORMAT = DOMAIN + ' {}'
SWITCH_NAME_FORMAT = DOMAIN + ' {}'

SENSOR_TYPES = {
    'volt_bat': ['BAT Voltage', 'V', 'battery', SensorDeviceClass.VOLTAGE],
    'volt_rpi': ['RPi Voltage', 'V', 'power-plug', SensorDeviceClass.VOLTAGE],
    'temp_ntc1': ['NTC1 Temperature', UnitOfTemperature.CELSIUS, 'thermometer', SensorDeviceClass.TEMPERATURE],
    'pwr_mode': ['Powering Mode', None, 'power', None],
}
SWITCH_TYPES = {
    'led_orange': ['Orange LED', 'led-off'],
    'led_green': ['Green LED', 'led-off'],
    'led_blue': ['Blue LED', 'led-off'],
    'led_enable': ['Enabled LEDs', 'led-off']
}

UPS_DATA = None


# NO ASYNC async def async_setup(hass, config):
def setup(hass, config):
    """Set up the UPS PIco component."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    entities = []

    global UPS_DATA
    UPS_DATA = UpsPico()
    UPS_DATA.get_data()

    #for object_id, cfg in SENSOR_TYPES.items():
    #    name = cfg[0]
    #    unit = cfg[1]
    #    icon = 'mdi:' + cfg[2]
    #    devClass = cfg[3]

    #    entities.append(UpsPicoSensor(object_id, name, unit, icon, devClass))

    #if not entities:
    #    return False

    # NO ASYNC async_track_time_interval(hass, UPS_DATA.async_update,
    track_time_interval(hass, UPS_DATA.update,
                              component.scan_interval)

    # yield from component.async_add_entities(entities)
    #component.add_entities(entities)
    return True


class UpsPico(object):
    """Class for UPS PIco i2c interface."""

    def __init__(self):
        """Initialize class."""
        import smbus2

        self.pico_reg = dict()
        self.pico_data = dict()
        self.i2c = smbus2.SMBus(1)
        self.reg_dict = {
            "led_orange": 0x09,
            "led_green": 0x0a,
            "led_blue": 0x0b,
            "led_enable": 0x15,
        }
        return

    def update(self, *_):
        """Async update latest data."""
        self.get_data()

    def _try_get_data(self):
        try:
            reg = self.i2c.read_i2c_block_data(0x69, 0, 0x1d)
            reg += [0xff, 0xff, 0xff]
            reg += (self.i2c.read_i2c_block_data(0x69, 0x20, 7))
            self.pico_reg[0x69] = reg

            reg = self.i2c.read_i2c_block_data(0x6b, 0, 0x16)
            self.pico_reg[0x6b] = reg

        except Exception as exc:
            _LOGGER.error('Except class UPS PIco _try_get_data(): ' + str(exc))
            return False

        return True

    def set_data(self, device, data):
        """Set data to UPS PIco."""
        addr = 0x6b
        if device in self.reg_dict:
            reg = self.reg_dict[device]
            try:
                self.i2c.write_byte_data(addr, reg, data)
                self.pico_data[device] = data
                _LOGGER.debug("Setting i2c addr %s %s to %s", addr, reg, data)
                return True
            except Exception as exc:
                _LOGGER.error('Except class PicoPlugin setData(): %s',
                              str(exc))
        else:
            _LOGGER.error('Error class PicoPlugin setData():'
                          'Unknown device %s', device)

        return False

    def led_on(self, device):
        """Turn LED on."""
        _LOGGER.debug("Turning device %s ON", device)
        return self.set_data(device, 1)

    def led_off(self, device):
        """Turn LED off."""
        _LOGGER.debug("Turning device %s OFF", device)
        return self.set_data(device, 0)

    def get_data(self):
        """Get data from UPS PIco."""
        result = self._try_get_data()

        if not result:
            return False

        # *** 0x69 registers
        data = self.pico_reg[0x69]

        # 0x69 0x00 Powering mode
        #reg_word = data[0x00]
        reg_word = data[0x00] & 0x01
        if reg_word == 1:
            self.pico_data["pwr_mode"] = "RPi powered"
        #elif reg_word == 2:
        elif reg_word == 0:
            self.pico_data["pwr_mode"] = "UPS powered"

        # 0x69 0x08 BAT voltage
        reg_word = int.from_bytes(data[0x08:0x0a], byteorder="little")
        reg_hex = format(reg_word, "02x")
        reg_volt = float(reg_hex) / 100
        self.pico_data["volt_bat"] = reg_volt

        # 0x69 0x0a RPi voltage
        reg_word = int.from_bytes(data[0x0a:0x0c], byteorder="little")
        reg_hex = format(reg_word, "02x")
        reg_volt = float(reg_hex) / 100
        self.pico_data["volt_rpi"] = reg_volt

        # 0x69 0x1b NTC1 temperature
        reg_word = data[0x1b]
        reg_hex = format(reg_word, "02x")
        self.pico_data["temp_ntc1"] = reg_hex

        # 0x69 0x24 PCB version
        reg_word = data[0x24]
        reg_chr = chr(reg_word)
        self.pico_data["ver_pcb"] = reg_chr

        # 0x69 0x25 Bootloader version
        reg_word = data[0x25]
        reg_chr = chr(reg_word)
        self.pico_data["ver_boot"] = reg_chr

        # 0x69 0x26 FW version
        reg_word = data[0x26]
        reg_hex = format(reg_word, "02x")
        self.pico_data["ver_fw"] = reg_hex

        # *** 0x6b registers
        data = self.pico_reg[0x6b]

        # 0x6b 0x01 Bat Powering time
        reg_word = data[0x01]
        if reg_word == 0xff:
            self.pico_data["pwr_runtime"] = "disabled"
        else:
            self.pico_data["pwr_runtime"] = 1 + reg_word

        # 0x6b 0x09, 0x0a, 0x0b User LEDs Orange, Green, Blue
        self.pico_data["led_orange"] = data[0x09]
        self.pico_data["led_green"] = data[0x0a]
        self.pico_data["led_blue"] = data[0x0b]

        # 0x6b 0x15 Enable LEDs
        self.pico_data["led_enable"] = data[0x15]

        return True
