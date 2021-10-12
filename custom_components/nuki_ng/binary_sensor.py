from homeassistant.components.binary_sensor import BinarySensorEntity

import logging

from . import NukiEntity, NukiBridge
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

    for dev_id in coordinator.data.get("devices", {}):
        entities.append(BatteryLow(coordinator, dev_id))
        entities.append(BatteryCharging(coordinator, dev_id))
        entities.append(LockState(coordinator, dev_id))
        if coordinator.device_supports(dev_id, "keypadBatteryCritical"):
            entities.append(KeypadBatteryLow(coordinator, dev_id))
        if coordinator.is_opener(dev_id):
            entities.append(RingAction(coordinator, dev_id))
        if coordinator.device_supports(dev_id, "doorsensorState"):
            entities.append(DoorState(coordinator, dev_id))
    entities.append(BridgeServerConnection(coordinator))
    entities.append(BridgeCallbackSet(coordinator))
    async_add_entities(entities)
    return True

class BatteryLow(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "battery_low")
        self.set_name("battery critical")

    @property
    def is_on(self) -> bool:
        return self.last_state.get("batteryCritical", False)

    @property
    def device_class(self) -> str:
        return "battery"

class BatteryCharging(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "battery_charging")
        self.set_name("battery charging")
        self._attr_device_class = "battery_charging"

    @property
    def is_on(self) -> bool:
        return self.last_state.get("batteryCharging", False)

class KeypadBatteryLow(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "keypad_battery_low")
        self.set_name("keypad battery critical")

    @property
    def is_on(self) -> bool:
        return self.last_state.get("keypadBatteryCritical", False)

    @property
    def device_class(self) -> str:
        return "battery"

class RingAction(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "ring_action")
        self.set_name("ring action")

    @property
    def is_on(self) -> bool:
        return self.last_state.get("ringactionState", False)

    @property
    def extra_state_attributes(self):
        return {
            "timestamp": self.last_state.get("ringactionTimestamp")
        }

class LockState(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "state")
        self.set_name("locked")
        self._attr_device_class = "lock"

    @property
    def is_on(self) -> bool:
        current = self.last_state.get("state", 255)
        return current in {2, 3, 4, 5, 6, 7}

    @property
    def extra_state_attributes(self):
        return {
            "timestamp": self.last_state.get("timestamp")
        }

class DoorState(NukiEntity, BinarySensorEntity):

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("binary_sensor", "door_state")
        self.set_name("door open")
        self._attr_device_class = "door"

    @property
    def is_on(self) -> bool:
        current = self.last_state.get("doorsensorState", 4)
        return current in {3}

class BridgeServerConnection(NukiBridge, BinarySensorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.set_id("connected")
        self.set_name("connected")
        self._attr_device_class = "connectivity"

    @property
    def is_on(self) -> bool:
        return self.data.get("serverConnected", False)

class BridgeCallbackSet(NukiBridge, BinarySensorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.set_id("callback_set")
        self.set_name("bridge callback set")
        self._attr_device_class = "connectivity"

    @property
    def is_on(self) -> bool:
        return self.data.get("callback_updated", False)

