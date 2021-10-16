from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.network import get_url
from .constants import DOMAIN
from .nuki import NukiInterface

import logging
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)


class OpenWrtConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_reauth(self, user_input):
        return await self.async_step_user(user_input)

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
        except Exception as err:
            _LOGGER.exception(f"Error getting list of devices: {err}")
            return []

    async def async_step_user(self, user_input):
        errors = None
        _LOGGER.debug(f"Input: {user_input}")
        if user_input is None:
            nuki = NukiInterface(self.hass)
            bridge_address = await nuki.discover_bridge()
            hass_url = get_url(self.hass)
            user_input = {
                "address": bridge_address,
                "hass_url": hass_url
            }

        if user_input.get("token"):
            devices = await self.find_nuki_devices(user_input)
            if len(devices) >= 1:
                title = user_input.get("name") or devices[0]["name"]
                return self.async_create_entry(
                    title=title,
                    data=user_input
                )
            errors = dict(base="bridge_error")
        schema = vol.Schema({
            vol.Required("address", default=user_input.get("address")): cv.string,
            vol.Required("hass_url", default=user_input.get("hass_url")): cv.string,
            vol.Required("token", default=user_input.get("token")): cv.string,
            vol.Optional("web_token", default=user_input.get("web_token", "")): cv.string,
            vol.Optional("name", default=user_input.get("name", "")): cv.string,
            vol.Required("update_seconds", default=user_input.get("update_seconds", 30)): vol.All(
                cv.positive_int,
                vol.Range(min=10, max=600)
            ),
        })
        return self.async_show_form(
            step_id="user", data_schema=schema
        )

    # def async_get_options_flow(config_entry):
    #     return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        data = self.config_entry.as_dict()["data"]
        _LOGGER.debug(f"OptionsFlowHandler: {data} {self.config_entry}")
        schema = vol.Schema({
            vol.Required("hass_url", default=data.get("hass_url")): cv.string,
            vol.Required("token", default=data.get("token")): cv.string,
            vol.Optional("web_token", default=data.get("web_token")): cv.string,
        })
        return self.async_show_form(
            step_id="options", data_schema=schema
        )
