from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _to_float(value: Any) -> float:
    """Safely convert a value to float, defaulting to 0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class LumoWaterCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        uuid: str,
        api_url: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        cold_price_per_1000: float = 0.0,
        warm_price_per_1000: float = 0.0,
    ) -> None:
        self.uuid = uuid
        self.api_url = api_url
        self.cold_price_per_liter = cold_price_per_1000 / 1000.0
        self.warm_price_per_liter = warm_price_per_1000 / 1000.0

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)

        try:
            response = await session.get(self.api_url, timeout=30)
            response.raise_for_status()
            data = await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching Lumo water data: {err}") from err

        raw_list = data.get("consumptions")
        if not isinstance(raw_list, list):
            raw_list = []

        consumptions: list[dict[str, Any]] = []
        seen_dates = set()

        for entry in raw_list:
            if not isinstance(entry, dict):
                continue
            date_str = entry.get("date", "")
            if not isinstance(date_str, str) or not date_str.strip():
                continue
            if date_str in seen_dates:
                continue
            seen_dates.add(date_str)

            consumptions.append(
                {
                    "date": date_str,
                    "coldLiters": _to_float(entry.get("coldLiters")),
                    "warmLiters": _to_float(entry.get("warmLiters")),
                }
            )

        consumptions.sort(key=lambda x: x["date"])

        total_cold = sum(c["coldLiters"] for c in consumptions)
        total_warm = sum(c["warmLiters"] for c in consumptions)

        latest = consumptions[-1] if consumptions else None

        today = datetime.now()
        month_prefix = f"{today.year}-{today.month:02d}"

        monthly_cold = sum(
            c["coldLiters"]
            for c in consumptions
            if c["date"].startswith(month_prefix)
        )
        monthly_warm = sum(
            c["warmLiters"]
            for c in consumptions
            if c["date"].startswith(month_prefix)
        )

        cold_cost = round(total_cold * self.cold_price_per_liter, 2)
        warm_cost = round(total_warm * self.warm_price_per_liter, 2)
        monthly_cold_cost = round(monthly_cold * self.cold_price_per_liter, 2)
        monthly_warm_cost = round(monthly_warm * self.warm_price_per_liter, 2)

        return {
            "consumptions": consumptions,
            "total_cold": total_cold,
            "total_warm": total_warm,
            "latest": latest,
            "monthly_cold": monthly_cold,
            "monthly_warm": monthly_warm,
            "cold_cost": cold_cost,
            "warm_cost": warm_cost,
            "monthly_cold_cost": monthly_cold_cost,
            "monthly_warm_cost": monthly_warm_cost,
            "contract_id": data.get("contractId", self.uuid),
        }
