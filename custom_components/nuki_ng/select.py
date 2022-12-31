from email.policy import default
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

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
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for dev_id in coordinator.data.get("devices", {}):
        if coordinator.info_field(dev_id, -1, "openerAdvancedConfig", "doorbellSuppression")  >= 0:
            entities.append(NukiOpenerRingSuppressionSelect(coordinator, dev_id))
    async_add_entities(entities)
    return True


class NukiOpenerRingSuppressionSelect(NukiEntity, SelectEntity):

    SUP_OFF = 0
    SUP_RING = 1
    SUP_RTO = 2
    SUP_CM = 4
    VALUES_TO_NAMES = {
      # 0
      SUP_OFF: 'Off',
      # 1
      SUP_RING: 'Ring',
      # 2
      SUP_RTO: 'Ring to Open',
      # 4
      SUP_CM: 'Continuous Mode',
      # 1 + 2 == 3
      SUP_RING | SUP_RTO: 'Ring & Ring to Open',
      # 1 + 4 == 5
      SUP_RING | SUP_CM: 'Ring & Continuous Mode',
      # 2 + 4 == 6
      SUP_RTO | SUP_CM: 'Ring to Open & Continuous Mode',
      # 1 + 2 + 4 == 7
      SUP_RING | SUP_RTO | SUP_CM: 'On (suppress all)',
    }
    NAMES_TO_VALUES = {v: k for k, v in VALUES_TO_NAMES.items()}

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("select", "ring_suppression")
        self.set_name("Ring suppression")
        self._attr_icon = "mdi:bell-cancel"

    @property
    def doorbellSuppression(self):
        return self.coordinator.info_field(self.device_id, 0, "openerAdvancedConfig", "doorbellSuppression")

    @property
    def current_option(self) -> str | None:
        return self.VALUES_TO_NAMES[self.doorbellSuppression]

    @property
    def options(self) -> list[str]:
        return self.NAMES_TO_VALUES.keys()

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    async def async_select_option(self, option: str) -> None:
        new_value = self.NAMES_TO_VALUES[option]
        await self.coordinator.update_config(self.device_id, "openerAdvancedConfig", dict(doorbellSuppression=new_value))
