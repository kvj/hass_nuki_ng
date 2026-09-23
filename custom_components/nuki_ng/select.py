from email.policy import default
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

import logging

from . import NukiEntity, NukiOpenerRingSuppressionEntity
from .constants import DOMAIN

_LOGGER = logging.getLogger(__name__)

BUTTON_PRESS_ACTIONS = {
    1: "Intelligent",
    2: "Unlock",
    3: "Lock",
    4: "Unlatch",
    5: "Lock 'n' Go",
    6: "Show status",
    0: "No action",
}


async def async_setup_entry(
    hass,
    entry,
    async_add_entities
):
    entities = []
    coordinator = entry.runtime_data

    for dev_id in coordinator.data.get("devices", {}):
        for config_key, name, id_suffix in (
            (
                "singleButtonPressAction",
                "Single button press action",
                "single_button_press_action",
            ),
            (
                "doubleButtonPressAction",
                "Double button press action",
                "double_button_press_action",
            ),
        ):
            if coordinator.info_field(
                dev_id, -1, "advancedConfig", config_key
            ) in BUTTON_PRESS_ACTIONS:
                entities.append(
                    NukiButtonPressActionSelect(
                        coordinator, dev_id, config_key, name, id_suffix
                    )
                )
        if coordinator.info_field(dev_id, -1, "openerAdvancedConfig", "doorbellSuppression")  >= 0:
            entities.append(NukiOpenerRingSuppressionSelect(coordinator, dev_id))
    async_add_entities(entities)
    return True


class NukiButtonPressActionSelect(NukiEntity, SelectEntity):
    NAMES_TO_VALUES = {v: k for k, v in BUTTON_PRESS_ACTIONS.items()}

    def __init__(self, coordinator, device_id, config_key, name, id_suffix):
        super().__init__(coordinator, device_id)
        self._config_key = config_key
        self.set_id("select", id_suffix)
        self.set_name(name)
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:gesture-tap-button"

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.info_field(
            self.device_id, -1, "advancedConfig", self._config_key
        )
        return BUTTON_PRESS_ACTIONS.get(value)

    @property
    def options(self) -> list[str]:
        return list(self.NAMES_TO_VALUES)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.update_config(
            self.device_id,
            "advancedConfig",
            {self._config_key: self.NAMES_TO_VALUES[option]},
        )


class NukiOpenerRingSuppressionSelect(NukiOpenerRingSuppressionEntity, SelectEntity):

    SUP_OFF = 0
    SUP_RING = NukiOpenerRingSuppressionEntity.SUP_RING
    SUP_RTO = NukiOpenerRingSuppressionEntity.SUP_RTO
    SUP_CM = NukiOpenerRingSuppressionEntity.SUP_CM

    VALUES_TO_NAMES = {
      # 0
      SUP_OFF: 'Off',
      # 4
      SUP_RING: 'Ring',
      # 2
      SUP_RTO: 'Ring to Open',
      # 1
      SUP_CM: 'Continuous Mode',
      # 4 + 2 == 6
      SUP_RING | SUP_RTO: 'Ring & Ring to Open',
      # 4 + 1 == 5
      SUP_RING | SUP_CM: 'Ring & Continuous Mode',
      # 2 + 1 == 3
      SUP_RTO | SUP_CM: 'Ring to Open & Continuous Mode',
      # 4 + 2 + 1 == 7
      SUP_RING | SUP_RTO | SUP_CM: 'On (suppress all)',
    }
    NAMES_TO_VALUES = {v: k for k, v in VALUES_TO_NAMES.items()}

    def __init__(self, coordinator, device_id):
        super().__init__(coordinator, device_id)
        self.set_id("select", "ring_suppression")
        self.set_name("Ring suppression")
        self._attr_icon = "mdi:bell-cancel"

    @property
    def current_option(self) -> str | None:
        return self.VALUES_TO_NAMES[self.doorbellSuppression]

    @property
    def options(self) -> list[str]:
        return list(self.NAMES_TO_VALUES.keys())

    async def async_select_option(self, option: str) -> None:
        await self.update_doorbell_suppression(self.NAMES_TO_VALUES[option])
