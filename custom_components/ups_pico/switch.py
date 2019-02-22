"""
UPS PIco switch platform.

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/
"""
import asyncio
import logging

# import voluptuous as vol

from homeassistant.components.switch import SwitchDevice
from custom_components import ups_pico

DEPENDENCIES = ['ups_pico']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the UPS PIco platform."""
    entities = []

    for object_id, cfg in ups_pico.SWITCH_TYPES.items():
        name = cfg[0]
        icon = 'mdi:' + cfg[1]

        entities.append(UpsPicoSwitch(object_id, name, icon))

    if not entities:
        return False

    async_add_devices(entities)
    return True


class UpsPicoSwitch(SwitchDevice):
    """Representation of UPS PIco switch."""

    def __init__(self, object_id, name, icon):
        """Initialize the switch."""
        self.ups_pico = ups_pico.UPS_DATA
        self._object_id = object_id
        self._name = ups_pico.SWITCH_NAME_FORMAT.format(name)
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
        self.ups_pico.led_on(self._object_id)
        self._state = True
        # self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.ups_pico.led_off(self._object_id)
        self._state = False
        # self.schedule_update_ha_state()

    def update(self):
        """Update switch state."""
        self._state = self.ups_pico.pico_data[self._object_id]
