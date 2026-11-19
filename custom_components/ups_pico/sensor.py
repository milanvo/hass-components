"""
UPS PIco sensor platform

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/
"""
import logging

from homeassistant.components.sensor import (
#    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from custom_components import ups_pico

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the UPS PIco component."""
    entities = []

    for object_id, cfg in ups_pico.SENSOR_TYPES.items():
        name = cfg[0]
        unit = cfg[1]
        icon = 'mdi:' + cfg[2]
        devClass = cfg[3]

        entities.append(UpsPicoSensor(object_id, name, unit, icon, devClass))

    if not entities:
        return False

    add_devices(entities)
    return True

class UpsPicoSensor(SensorEntity):
    """Representation of UPS PIco sensor."""

    def __init__(self, object_id, name, unit, icon, devClass):
        """Initialize the sensor."""
        self.ups_pico = ups_pico.UPS_DATA
        self._object_id = object_id
        self._attr_name = ups_pico.SENSOR_NAME_FORMAT.format(name)
        self._attr_native_value = self.ups_pico.pico_data[self._object_id] or None
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

        self._attr_device_class = devClass
        if devClass:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = object_id

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    @property
    def state_attributes(self):
        """Return the state attributes of the UPS."""
        if self._object_id == 'pwr_mode':
            attrs = {
                'pwr_runtime': self.ups_pico.pico_data['pwr_runtime'],
                'ver_pcb': self.ups_pico.pico_data['ver_pcb'],
                'ver_boot': self.ups_pico.pico_data['ver_boot'],
                'ver_fw': self.ups_pico.pico_data['ver_fw'],
            }
            return attrs
        return None

    def update(self):
        """Update sensor state."""
        self._attr_native_value = self.ups_pico.pico_data[self._object_id]

