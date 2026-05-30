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
