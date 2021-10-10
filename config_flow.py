from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .constants import DOMAIN
from .nuki import NukiInterface

import logging
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("address"): cv.string,
    vol.Required("token"): cv.string,
    vol.Optional("web_token"): cv.string,
})

class OpenWrtConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_reauth(self, user_input):
        return await self.async_step_user(user_input)

    async def schema_with_bridge(self):
        nuki = NukiInterface(self.hass)
        bridge_address = await nuki.discover_bridge()
        if bridge_address:
            return STEP_USER_DATA_SCHEMA.extend({
                vol.Required("address", default=bridge_address): cv.string,
            })
        return STEP_USER_DATA_SCHEMA


    async def find_nuki_devices(self, config: dict):
        nuki = NukiInterface(
            self.hass, 
            bridge=config["address"], 
            token=config["token"]
        )
        try:
            statuses = await nuki.bridge_list()
            _LOGGER.debug(f"bridge_list: {statuses}")
            return list(map(lambda x: dict(
                id=x["nukiId"], name=x["name"]
            ), statuses))
        except ConnectionError as err:
            _LOGGER.exception(f"Error getting list of devices: {err}")
            return []

    async def async_step_user(self, user_input):
        if user_input is None:
            schema = await self.schema_with_bridge()
            return self.async_show_form(
                step_id="user", data_schema=schema
            )
        _LOGGER.debug(f"Input: {user_input}")
        devices = await self.find_nuki_devices(user_input)
        if len(devices) < 1:
            errors = dict(base="bridge_error")
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )
        return self.async_create_entry(
            title=devices[0]["name"], 
            data=user_input
        )
