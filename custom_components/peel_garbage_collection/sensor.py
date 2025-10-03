"""Sensor platform for Peel Garbage Collection integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import PeelGarbageDataUpdateCoordinator
    from .peel_region_api import CollectionScheduleCalendarEntry

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="next_collection",
        name="Next Collection Date",
        icon="mdi:calendar",
    ),
    SensorEntityDescription(
        key="collection_types",
        name="Collection Types",
        icon="mdi:trash-can",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Peel Garbage Collection sensors from config entry."""
    coordinator: PeelGarbageDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities = [PeelGarbageSensor(coordinator, desc) for desc in SENSOR_TYPES]

    async_add_entities(entities)


class PeelGarbageSensor(SensorEntity):
    """Representation of a Peel Garbage Collection sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PeelGarbageDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator._attr_device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self._coordinator.data:
            return None

        calendar_entries: list[CollectionScheduleCalendarEntry] = self._coordinator.data  # type: ignore
        if len(calendar_entries) == 0:
            return None

        calendar_entry = calendar_entries[0]

        if self.entity_description.key == "next_collection":
            next_date = calendar_entry.date
            if next_date:
                return next_date.date()  # type: ignore
            return None

        if self.entity_description.key == "collection_types":
            return ", ".join(calendar_entry.types)

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success
