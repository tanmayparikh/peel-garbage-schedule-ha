"""The Garbage Collection integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

_LOGGER = logging.getLogger(__name__)

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


from .const import DOMAIN
from .coordinator import PeelGarbageDataUpdateCoordinator

CURRENT_VERSION = 2

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Garbage Collection component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garbage Collection from a config entry."""
    coordinator = PeelGarbageDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries — VERSION 1 requires reconfiguration."""
    _LOGGER.warning(
        "Config entry %s is version %s, current version is %s. "
        "Please remove and re-add the integration to pick up the new recycling source.",
        entry.entry_id,
        entry.version,
        CURRENT_VERSION,
    )
    return False
