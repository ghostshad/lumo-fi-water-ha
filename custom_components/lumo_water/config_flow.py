import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_URL, DOMAIN

CONFIG_SCHEMA = vol.Schema({vol.Required("uuid"): str})


class LumoWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            uuid = user_input["uuid"]

            await self.async_set_unique_id(uuid)
            self._abort_if_unique_id_configured()

            if not await self._test_connection(uuid):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Lumo Water",
                    data={"uuid": uuid},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, uuid: str) -> bool:
        session = async_get_clientsession(self.hass)
        try:
            response = await session.get(API_URL.format(uuid=uuid), timeout=30)
            if response.status != 200:
                return False
            data = await response.json()
            return "contractId" in data and "consumptions" in data
        except Exception:
            return False
