"""DataUpdateCoordinator for the Peel Garbage Collection integration."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CircularMaterialsAPI,
    CollectionScheduleCalendarEntry,
    CollectionType,
    PeelRegionAPI,
)
from .const import (
    CONF_CIRCULAR_DISTRICT_ID,
    CONF_CIRCULAR_PROJECT_ID,
    CONF_CIRCULAR_ZONE_ID,
    CONF_PEEL_PLACE_ID,
    CONF_PEEL_TITLE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PeelGarbageDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Peel Garbage Collection data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self.config_entry = config_entry

        self._peel_api = PeelRegionAPI(hass)
        self._place_id: str = config_entry.data[CONF_PEEL_PLACE_ID]

        self._circular_api = CircularMaterialsAPI(hass)
        self._district_id: str = config_entry.data[CONF_CIRCULAR_DISTRICT_ID]
        self._project_id: str = config_entry.data[CONF_CIRCULAR_PROJECT_ID]
        self._zone_id: str = config_entry.data[CONF_CIRCULAR_ZONE_ID]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.data[CONF_PEEL_TITLE],
            manufacturer="Peel Region",
            model="Garbage Collection Schedule",
            entry_type=DeviceEntryType.SERVICE,
        )  # type: ignore[arg-type]

    async def _async_update_data(self) -> list[CollectionScheduleCalendarEntry]:
        """Fetch and merge data from both collection APIs."""
        try:
            peel_entries, recycling_entries = await asyncio.gather(
                self._peel_api.get_collection_schedule(self._place_id),
                self._circular_api.get_collection_schedule(
                    self._project_id, self._district_id, self._zone_id
                ),
            )
        except Exception as err:
            msg = f"Error communicating with API: {err}"
            raise UpdateFailed(msg) from err

        merged: dict[str, CollectionScheduleCalendarEntry] = {
            entry.date.strftime("%Y-%m-%d"): entry for entry in (peel_entries or [])
        }

        for entry in recycling_entries or []:
            key = entry.date.strftime("%Y-%m-%d")
            if key in merged:
                merged[key].types.append(CollectionType.Recycling)
            else:
                merged[key] = entry

        return sorted(merged.values(), key=lambda e: e.date)
