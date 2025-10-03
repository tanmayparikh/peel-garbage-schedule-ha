"""DataUpdateCoordinator for the Peel Garbage Collection integration."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .peel_region_api import PeelRegionAPI

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
        self.api = PeelRegionAPI(hass)
        self.config_entry = config_entry
        self.place_id = config_entry.data["place_id"]

        addr = config_entry.data["title"]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=addr,
            manufacturer="Peel Region",
            model="Garbage Collection Schedule",
            entry_type=DeviceEntryType.SERVICE,
        )  # type: ignore

    async def _async_update_data(self):
        """Fetch data from Peel Region API."""
        try:
            return await self.api.get_collection_schedule(self.place_id)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
