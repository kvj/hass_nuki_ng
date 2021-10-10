from homeassistant.components.sensor import SensorEntity

import logging

from . import NukiEntity
from .constants import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass,
    entry,
    async_add_entities
):
    entities = []
    data = entry.as_dict()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for dev_id in coordinator.data:
        entities.append(Battery(coordinator, dev_id))
        entities.append(LockState(coordinator, dev_id))
        if coordinator.device_supports(dev_id, "doorsensorStateName"):
            entities.append(DoorSensorState(coordinator, dev_id))
    async_add_entities(entities)
    return True

class Battery(NukiEntity, SensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "battery")
        self.set_name("battery")
        self._attr_device_class = "battery"

    @property
    def state(self):
        value = self.last_state.get("batteryChargeState", 0)
        return f"{value}%"

class LockState(NukiEntity, SensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "state")
        self.set_name("state")
        self._attr_icon = "mdi:door"

    @property
    def state(self):
        return self.last_state.get("stateName")

class DoorSensorState(NukiEntity, SensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "door_state")
        self.set_name("door state")
        self._attr_icon = "mdi:door-open"

    @property
    def state(self):
        return self.last_state.get("doorsensorStateName")
