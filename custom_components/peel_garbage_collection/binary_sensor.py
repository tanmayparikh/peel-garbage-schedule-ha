"""Binary Sensor platform for Peel Garbage Collection integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from custom_components.peel_garbage_collection.peel_region_api import CollectionType

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import PeelGarbageDataUpdateCoordinator
    from .peel_region_api import CollectionScheduleCalendarEntry

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="next_collection_recycling",
        name="Next Collection Recycling",
        icon="mdi:recycle",
    ),
    BinarySensorEntityDescription(
        key="next_collection_organics",
        name="Next Collection Organics",
        icon="mdi:leaf-circle",
    ),
    BinarySensorEntityDescription(
        key="next_collection_garbage",
        name="Next Collection Garbage",
        icon="mdi:trash-can",
    ),
    BinarySensorEntityDescription(
        key="next_collection_yardwaste",
        name="Next Collection Yard Waste",
        icon="mdi:grass",
    ),
    BinarySensorEntityDescription(
        key="next_collection_garbage_exemption",
        name="Next Collection Garbage Exemption Day",
        icon="mdi:delete-restore",
    ),
    BinarySensorEntityDescription(
        key="next_collection_battery_collection",
        name="Next Collection Battery Collection Day",
        icon="mdi:battery-60",
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

    entities = [
        PeelGarbageBinarySensor(coordinator, desc) for desc in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities)


class PeelGarbageBinarySensor(BinarySensorEntity):
    """Representation of a Peel Garbage Type Collection sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PeelGarbageDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator._attr_device_info

    @property
    def is_on(self) -> StateType:
        """Return the state of the sensor."""
        if not self._coordinator.data:
            return None

        calendar_entries: list[CollectionScheduleCalendarEntry] = self._coordinator.data  # type: ignore
        if len(calendar_entries) == 0:
            return None

        calendar_entry = calendar_entries[0]

        if self.entity_description.key == "next_collection_recycling":
            return CollectionType.Recycling in calendar_entry.types

        if self.entity_description.key == "next_collection_organics":
            return CollectionType.Organics in calendar_entry.types

        if self.entity_description.key == "next_collection_garbage":
            return CollectionType.Garbage in calendar_entry.types

        if self.entity_description.key == "next_collection_yardwaste":
            return CollectionType.YardWaste in calendar_entry.types

        if self.entity_description.key == "next_collection_garbage_exemption":
            return CollectionType.GarbageExemption in calendar_entry.types

        if self.entity_description.key == "next_collection_battery_collection":
            return CollectionType.Battery in calendar_entry.types

        return None

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success
