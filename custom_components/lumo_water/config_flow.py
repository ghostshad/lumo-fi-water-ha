import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_URL,
    CONF_COLD_PRICE,
    CONF_WARM_PRICE,
    DEFAULT_API_URL,
    DOMAIN,
)

CONFIG_SCHEMA = vol.Schema({vol.Required("uuid"): str})

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_URL): str,
        vol.Optional(CONF_COLD_PRICE, default=0.0): vol.Coerce(float),
        vol.Optional(CONF_WARM_PRICE, default=0.0): vol.Coerce(float),
    }
)


class LumoWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            uuid = user_input["uuid"]

            await self.async_set_unique_id(uuid)
            self._abort_if_unique_id_configured()

            api_url = DEFAULT_API_URL.format(uuid=uuid)

            if not await self._test_connection(api_url):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Lumo Water",
                    data={"uuid": uuid, CONF_API_URL: api_url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, api_url: str) -> bool:
        session = async_get_clientsession(self.hass)
        try:
            response = await session.get(api_url, timeout=30)
            if response.status != 200:
                return False
            data = await response.json()
            return "contractId" in data and "consumptions" in data
        except Exception:
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LumoWaterOptionsFlow()


class LumoWaterOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options or {}
        data = self.config_entry.data or {}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_API_URL,
                        default=options.get(CONF_API_URL, data.get(CONF_API_URL, "")),
                    ): str,
                    vol.Optional(
                        CONF_COLD_PRICE,
                        default=options.get(CONF_COLD_PRICE, 0.0),
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_WARM_PRICE,
                        default=options.get(CONF_WARM_PRICE, 0.0),
                    ): vol.Coerce(float),
                }
            ),
        )
