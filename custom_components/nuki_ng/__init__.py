from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .nuki import NukiCoordinator
from .constants import DOMAIN, PLATFORMS

OPENER_TYPE = 1
LOCK_TYPE = 0

_LOGGER = logging.getLogger(__name__)


# ------------------------------------------------------
#  Home Assistant Setup
# ------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = entry.as_dict()["data"]
    _LOGGER.debug(f"async_setup_entry: {data}")

    coordinator = NukiCoordinator(hass, entry, data)
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    coordinator = entry.runtime_data
    await coordinator.unload()
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    entry.runtime_data = None
    return True


def _register_coordinator_service(hass: HomeAssistant, name: str, handler):
    async def handler_(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            if entry := hass.config_entries.async_get_entry(entry_id):
                if entry.domain == DOMAIN:
                    _LOGGER.debug(f"service call: {name} for {entry.domain}")
                    handler(entry.runtime_data, call.data)

    hass.services.async_register(DOMAIN, name, handler_)


async def async_setup(hass: HomeAssistant, config) -> bool:
    _register_coordinator_service(
        hass,
        "bridge_reboot",
        lambda coord, _: hass.async_create_task(coord.do_reboot()),
    )
    _register_coordinator_service(
        hass,
        "bridge_fwupdate",
        lambda coord, _: hass.async_create_task(coord.do_fwupdate()),
    )
    _register_coordinator_service(
        hass,
        "bridge_delete_callback",
        lambda coord, data: hass.async_create_task(
            coord.do_delete_callback(data.get("callback"))
        ),
    )
    _register_coordinator_service(
        hass,
        "execute_action",
        lambda coord, data: hass.async_create_task(
            coord.action_for_devices(data.get("action"))
        ),
    )

    return True


# ------------------------------------------------------
#  Nuki Base Entities
# ------------------------------------------------------

class NukiEntity(CoordinatorEntity):
    """Base entity for Nuki locks and openers."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator)
        self.device_id = device_id

    # ---- ID + Name helpers -------------------------------------

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

    # ---- Data Access --------------------------------------------

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
        return "Nuki Device"

    # ---- FIXED device_info --------------------------------------

    @property
    def device_info(self):
        """
        Correct HA-compatible device definition.
        Ensures:
        - identifiers use (DOMAIN, id)
        - via_device only set if bridge_id exists
        """
        # Bridge Hardware-ID (may be None)
        bridge_id = self.coordinator.info_data().get("ids", {}).get("hardwareId")

        info = {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.get_name,
            "manufacturer": "Nuki",
            "model": self.model,
            "sw_version": self.data.get("firmwareVersion"),
        }

        # Add bridging only when valid
        if bridge_id:
            info["via_device"] = (DOMAIN, bridge_id)

        return info


# ------------------------------------------------------
#  Nuki Bridge Entity
# ------------------------------------------------------

class NukiBridge(CoordinatorEntity):
    """Represents the Nuki Bridge device."""

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
        """Correct HA-compliant Bridge info."""
        model = (
            "Hardware Bridge"
            if self.data.get("bridgeType", 1) == 1
            else "Software Bridge"
        )
        versions = self.data.get("versions", {})

        return {
            "identifiers": {(DOMAIN, self.get_id)},
            "name": "Nuki Bridge",
            "manufacturer": "Nuki",
            "model": model,
            "sw_version": versions.get("firmwareVersion"),
        }


# ------------------------------------------------------
#  Advanced Opener Entity
# ------------------------------------------------------

class NukiOpenerRingSuppressionEntity(NukiEntity):

    SUP_RING = 4
    SUP_RTO = 2
    SUP_CM = 1

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def doorbellSuppression(self):
        return self.coordinator.info_field(
            self.device_id, 0, "openerAdvancedConfig", "doorbellSuppression"
        )

    async def update_doorbell_suppression(self, new_value):
        await self.coordinator.update_config(
            self.device_id,
            "openerAdvancedConfig",
            dict(doorbellSuppression=new_value),
        )

