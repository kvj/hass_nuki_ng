from __future__ import annotations
from .nuki import NukiCoordinator
from .constants import DOMAIN, PLATFORMS

from homeassistant.core import HomeAssistant
from homeassistant.helpers import service, entity_registry, device_registry
from homeassistant.helpers.entity import EntityCategory

# from homeassistant.helpers import device_registry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

import logging

OPENER_TYPE = 1
LOCK_TYPE = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = entry.as_dict()["data"]
    _LOGGER.debug(f"async_setup_entry: {data}")

    coordinator = NukiCoordinator(hass, entry, data)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    await hass.data[DOMAIN][entry.entry_id].unload()
    for p in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, p)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def _extract_dev_ids(hass, service_call) -> set[str]:
    entity_ids = await service.async_extract_entity_ids(hass, service_call)
    result = set()
    entity_reg = entity_registry.async_get(hass)
    device_reg = device_registry.async_get(hass)
    for id in entity_ids:
        if entry := entity_reg.async_get(id):
            if device := device_reg.async_get(entry.device_id):
                ids = {x[0]: x[1] for x in device.identifiers}
                result.add((entry.config_entry_id, ids.get("id")))
    return result


async def async_setup(hass: HomeAssistant, config) -> bool:
    hass.data[DOMAIN] = dict()

    async def async_reboot(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            await hass.data[DOMAIN][entry_id].do_reboot()

    async def async_fwupdate(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            await hass.data[DOMAIN][entry_id].do_fwupdate()

    async def async_delete_callback(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            await hass.data[DOMAIN][entry_id].do_delete_callback(
                call.data.get("callback")
            )

    async def async_exec_action(call):
        for entry_id, dev_id in await _extract_dev_ids(hass, call):
            await hass.data[DOMAIN][entry_id].action(dev_id, call.data.get("action"))

    hass.services.async_register(DOMAIN, "bridge_reboot", async_reboot)
    hass.services.async_register(DOMAIN, "bridge_fwupdate", async_fwupdate)
    hass.services.async_register(
        DOMAIN, "bridge_delete_callback", async_delete_callback
    )
    hass.services.async_register(DOMAIN, "execute_action", async_exec_action)

    return True


class NukiEntity(CoordinatorEntity):
    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator)
        self.device_id = device_id

    def set_id(self, prefix: str, suffix: str):
        self.id_prefix = prefix
        self.id_suffix = suffix

    def set_name(self, name: str):
        self._attr_name_suffix = name

    @property
    def name_suffix(self):
        return self._attr_name_suffix

    @property
    def get_name(self):
        return "Nuki %s" % (self.data.get("name", self.device_id))

    @property
    def name(self) -> str:
        return "%s %s" % (self.get_name, self.name_suffix)

    @property
    def unique_id(self) -> str:
        return "nuki-%s-%s" % (self.device_id, self.id_suffix)

    @property
    def available(self):
        if "nukiId" not in self.data:
            return False
        return super().available

    @property
    def data(self) -> dict:
        return self.coordinator.device_data(self.device_id)

    @property
    def last_state(self) -> dict:
        return self.data.get("lastKnownState", {})

    @property
    def model(self) -> str:
        if self.coordinator.is_lock(self.device_id):
            return "Nuki Smart Lock"
        if self.coordinator.is_opener(self.device_id):
            return "Nuki Opener"

    @property
    def device_info(self):
        return {
            "identifiers": {("id", self.device_id)},
            "name": self.get_name,
            "manufacturer": "Nuki",
            "model": self.model,
            "sw_version": self.data.get("firmwareVersion"),
            "via_device": (
                "id",
                self.coordinator.info_data().get("ids", {}).get("hardwareId"),
            ),
        }


class NukiBridge(CoordinatorEntity):
    def set_id(self, suffix: str):
        self.id_suffix = suffix

    def set_name(self, name: str):
        self.name_suffix = name

    @property
    def name(self) -> str:
        return "Nuki Bridge %s" % (self.name_suffix)

    @property
    def unique_id(self) -> str:
        return "nuki-bridge-%s-%s" % (self.get_id, self.id_suffix)

    @property
    def data(self) -> dict:
        return self.coordinator.data.get("bridge_info", {})

    @property
    def get_id(self):
        return self.data.get("ids", {}).get("hardwareId")

    @property
    def device_info(self):
        model = (
            "Hardware Bridge" if self.data.get("bridgeType", 1) == 1 else "Software Bridge"
        )
        versions = self.data.get("versions", {})
        return {
            "identifiers": {("id", self.get_id)},
            "name": "Nuki Bridge",
            "manufacturer": "Nuki",
            "model": model,
            "sw_version": versions.get("firmwareVersion"),
        }


class NukiOpenerRingSuppressionEntity(NukiEntity):
    
    SUP_RING = 4
    SUP_RTO = 2
    SUP_CM = 1
    
    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def doorbellSuppression(self):
        return self.coordinator.info_field(self.device_id, 0, "openerAdvancedConfig", "doorbellSuppression")
    
    async def update_doorbell_suppression(self, new_value):
        await self.coordinator.update_config(self.device_id, "openerAdvancedConfig", dict(doorbellSuppression=new_value))
