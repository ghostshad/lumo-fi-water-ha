# Lumo Water — Home Assistant Custom Integration

## Overview

Fetches daily water consumption data (cold/warm liters) from Lumo Finland's API
at `https://customer.mylumoapp.lumo.fi/api/contract-water-consumption/<UUID>`
and exposes it in Home Assistant as 6 sensor entities.

## File Structure

```
custom_components/lumo_water/
├── __init__.py
├── manifest.json
├── const.py
├── strings.json
├── config_flow.py
├── coordinator.py
└── sensor.py
```

---

## File 1: `custom_components/lumo_water/manifest.json`

```json
{
  "domain": "lumo_water",
  "name": "Lumo Water Consumption",
  "codeowners": ["@lumo-water"],
  "version": "1.0.0",
  "requirements": [],
  "iot_class": "cloud_polling",
  "config_flow": true,
  "documentation": "https://github.com/lumo-water/ha-lumo-water",
  "issue_tracker": "https://github.com/lumo-water/ha-lumo-water/issues",
  "integration_type": "device"
}
```

---

## File 2: `custom_components/lumo_water/const.py`

```python
DOMAIN = "lumo_water"
API_URL = "https://customer.mylumoapp.lumo.fi/api/contract-water-consumption/{uuid}"
DEFAULT_SCAN_INTERVAL = 21600
CONF_UUID = "uuid"
ATTRIBUTION = "Data provided by Lumo Finland"
```

---

## File 3: `custom_components/lumo_water/strings.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Lumo Water Consumption",
        "description": "Enter your contract UUID from the Lumo water consumption API URL.",
        "data": {
          "uuid": "Contract UUID"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to the API. Check the UUID and try again.",
      "unknown": "An unknown error occurred."
    },
    "abort": {
      "already_configured": "This UUID is already configured."
    }
  }
}
```

---

## File 4: `custom_components/lumo_water/config_flow.py`

```python
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
```

---

## File 5: `custom_components/lumo_water/coordinator.py`

```python
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
            "contract_id": data.get("contractId", uuid),
        }
```

---

## File 6: `custom_components/lumo_water/sensor.py`

```python
from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import LumoWaterCoordinator

SENSOR_DEFINITIONS = [
    {
        "key": "cold_consumption",
        "name": "Cold Consumption",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "value_fn": lambda data: data["total_cold"],
    },
    {
        "key": "warm_consumption",
        "name": "Warm Consumption",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "value_fn": lambda data: data["total_warm"],
    },
    {
        "key": "cold_daily",
        "name": "Cold Daily",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda data: (
            data["latest"].get("coldLiters", 0) if data["latest"] else 0
        ),
    },
    {
        "key": "warm_daily",
        "name": "Warm Daily",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda data: (
            data["latest"].get("warmLiters", 0) if data["latest"] else 0
        ),
    },
    {
        "key": "cold_monthly",
        "name": "Cold Monthly",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda data: data["monthly_cold"],
    },
    {
        "key": "warm_monthly",
        "name": "Warm Monthly",
        "icon": "mdi:water",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda data: data["monthly_warm"],
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LumoWaterCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        LumoWaterSensor(coordinator, entry, definition)
        for definition in SENSOR_DEFINITIONS
    )


class LumoWaterSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: LumoWaterCoordinator,
        entry: ConfigEntry,
        definition: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._definition = definition
        self._attr_has_entity_name = True
        self._attr_name = definition["name"]
        self._attr_unique_id = f"{entry.data['uuid']}_{definition['key']}"
        self._attr_icon = definition["icon"]
        self._attr_native_unit_of_measurement = definition["native_unit_of_measurement"]
        self._attr_state_class = definition["state_class"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["uuid"])},
            name="Lumo Water Meter",
            manufacturer="Lumo Finland",
            model="Water Consumption",
        )
        self._attr_translation_key = definition["key"]

    @property
    def native_value(self) -> float | int | None:
        data = self.coordinator.data
        if data is None:
            return None
        return self._definition["value_fn"](data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        attrs: dict[str, Any] = {"attribution": ATTRIBUTION}

        if data is not None:
            attrs["consumptions"] = data["consumptions"]
            attrs["data_count"] = len(data["consumptions"])
            if data["latest"]:
                attrs["last_data_date"] = data["latest"]["date"]
            if "monthly" in self._definition["key"]:
                attrs["month"] = date.today().strftime("%Y-%m")

        return attrs
```

---

## File 7: `custom_components/lumo_water/__init__.py`

```python
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LumoWaterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = LumoWaterCoordinator(hass, entry.data["uuid"])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return True
```

---

## Sensor Entities

| Entity ID | State Class | Unit | Value |
|---|---|---|---|
| `sensor.lumo_water_cold_consumption` | `total_increasing` | L | All-time cumulative cold |
| `sensor.lumo_water_warm_consumption` | `total_increasing` | L | All-time cumulative warm |
| `sensor.lumo_water_cold_daily` | `measurement` | L | Latest available day's cold |
| `sensor.lumo_water_warm_daily` | `measurement` | L | Latest available day's warm |
| `sensor.lumo_water_cold_monthly` | `measurement` | L | Current calendar month cold sum |
| `sensor.lumo_water_warm_monthly` | `measurement` | L | Current calendar month warm sum |

All sensors carry the full consumption array in `extra_state_attributes` under
the `consumptions` key, plus metadata (`data_count`, `last_data_date`, `attribution`).

---

## Installation Instructions

1. **Copy the integration** — place the entire `custom_components/lumo_water/` folder
   into your Home Assistant `config/custom_components/` directory.

   ```
   config/
   └── custom_components/
       └── lumo_water/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── strings.json
           ├── config_flow.py
           ├── coordinator.py
           └── sensor.py
   ```

2. **Restart Home Assistant** — `Settings > System > Restart` or `ha core restart`.

3. **Add the integration**:
   - Go to `Settings > Devices & Services`
   - Click `Add Integration` (bottom right)
   - Search for `Lumo Water Consumption`
   - Enter your UUID (the path segment from the API URL after `/api/contract-water-consumption/`)
   - Submit

4. **Verify** — after setup, 6 sensor entities appear immediately. Check `Developer Tools > States`
   for `sensor.lumo_water_cold_consumption` etc. First data poll runs immediately,
   subsequent polls every **6 hours** (configurable in `const.py`).

5. **Graphing** — use the **Energy dashboard** for cumulative sensors (add as Water),
   or the **History panel** / **Statistics graph** cards for daily/monthly sensors.

## Troubleshooting

- **Integration not found in search** — verify `manifest.json` is valid JSON and
  the folder is at `custom_components/lumo_water/` (not nested deeper).
- **"Failed to connect" during setup** — check that the UUID is correct and the
  API is reachable from your HA instance. Try `curl` on the API URL from the HA machine.
- **No data after setup** — check `Settings > System > Logs` for errors.
  The coordinator logs fetch failures at `warning` level.
- **Data is a few days behind** — this is expected. The Lumo API does not update
  daily. The integration polls every 6 hours and picks up whatever data is available.

## Updating `scan_interval`

The default polling interval is 6 hours (21600 seconds). To change it, edit
`const.py`:

```python
DEFAULT_SCAN_INTERVAL = 21600  # change to desired seconds (e.g., 43200 for 12h)
```

Then restart HA.
