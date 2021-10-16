from homeassistant.components.sensor import SensorEntity

import logging

from . import NukiEntity
from .constants import DOMAIN
from .states import DoorSensorStates, LockStates, DoorSecurityStates

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    entities = []
    data = entry.as_dict()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for dev_id in coordinator.data.get("devices", {}):
        entities.append(LockState(coordinator, dev_id))
        entities.append(RSSI(coordinator, dev_id))
        if coordinator.device_supports(dev_id, "batteryChargeState"):
            entities.append(Battery(coordinator, dev_id))
        if coordinator.device_supports(dev_id, "doorsensorStateName"):
            entities.append(DoorSensorState(coordinator, dev_id))
            entities.append(DoorSecurityState(coordinator, dev_id))
    async_add_entities(entities)
    return True


class Battery(NukiEntity, SensorEntity):
    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "battery")
        self.set_name("Battery")
        self._attr_device_class = "battery"
        self._attr_state_class = "measurement"

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def native_value(self):
        return self.last_state.get("batteryChargeState", 0)

    @property
    def state(self):
        return self.native_value


class LockState(NukiEntity, SensorEntity):
    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "state")
        self.set_name("State")
        self._attr_icon = "mdi:door"

    @property
    def state(self):
        return self.last_state.get("stateName")


class RSSI(NukiEntity, SensorEntity):
    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "rssi")
        self.set_name("RSSI")
        self._attr_device_class = "signal_strength"
        self._attr_state_class = "measurement"

    @property
    def native_unit_of_measurement(self):
        return "dBm"

    @property
    def native_value(self):
        return self.data.get("bridgeInfo", {}).get("rssi")

    @property
    def state(self):
        return self.native_value


class DoorSensorState(NukiEntity, SensorEntity):
    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "door_state")
        self.set_name("Door State")
        self._attr_icon = "mdi:door"

    @property
    def state(self):
        return self.last_state.get("doorsensorStateName")


class DoorSecurityState(NukiEntity, SensorEntity):
    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("sensor", "door_security_state")
        self.set_name("Door Security State")
        self._attr_icon = "mdi:door-closed-lock"

    @property
    def icon(self):

        state = self.get_state()

        if state == DoorSecurityStates.CLOSED_AND_LOCKED:
            return "mdi:door-closed-lock"
        elif state == DoorSecurityStates.CLOSED_AND_UNLOCKED:
            return "mdi:door-closed"
        return "mdi:door-open"

    @property
    def state(self):
        return str(self.get_state())

    def get_state(self) -> DoorSecurityStates:
        lock_state = LockStates(self.last_state.get("state"))
        door_sensor_state = DoorSensorStates(
            self.last_state.get("doorsensorState"))

        if lock_state == LockStates.LOCKED and door_sensor_state == DoorSensorStates.DOOR_CLOSED:
            return DoorSecurityStates.CLOSED_AND_LOCKED
        elif door_sensor_state == DoorSensorStates.DOOR_CLOSED:
            return DoorSecurityStates.CLOSED_AND_UNLOCKED
        return DoorSecurityStates.OPEN
