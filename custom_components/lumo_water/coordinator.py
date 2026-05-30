from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class LumoWaterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, uuid: str) -> None:
        self.uuid = uuid
        self.api_url = API_URL.format(uuid=uuid)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)

        try:
            response = await session.get(self.api_url, timeout=30)
            response.raise_for_status()
            data = await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching Lumo water data: {err}") from err

        consumptions: list[dict[str, Any]] = data.get("consumptions", [])
        consumptions.sort(key=lambda x: x.get("date", ""))

        total_cold = sum(c.get("coldLiters", 0) for c in consumptions)
        total_warm = sum(c.get("warmLiters", 0) for c in consumptions)

        latest = consumptions[-1] if consumptions else None

        today = datetime.now()
        month_prefix = f"{today.year}-{today.month:02d}"

        monthly_cold = sum(
            c.get("coldLiters", 0)
            for c in consumptions
            if c.get("date", "").startswith(month_prefix)
        )
        monthly_warm = sum(
            c.get("warmLiters", 0)
            for c in consumptions
            if c.get("date", "").startswith(month_prefix)
        )

        return {
            "consumptions": consumptions,
            "total_cold": total_cold,
            "total_warm": total_warm,
            "latest": latest,
            "monthly_cold": monthly_cold,
            "monthly_warm": monthly_warm,
            "contract_id": data.get("contractId", self.uuid),
        }
