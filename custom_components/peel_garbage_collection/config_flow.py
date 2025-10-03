"""Config flow for Peel Garbage Collection integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS, DOMAIN
from .peel_region_api import PeelRegionAPI

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    address = data[CONF_ADDRESS].strip()
    if not address:
        raise InvalidAddressError(
            translation_domain=DOMAIN,
            translation_key="error.empty_address",
        )

    api = PeelRegionAPI(hass)
    result = await api.search_address(address)
    if not result:
        raise InvalidAddressError(
            translation_domain=DOMAIN,
            translation_key="error.invalid_address",
        )

    # Return info that you want to store in the config entry.
    return {"title": result["name"], "place_id": result["place_id"]}


class AddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Peel Garbage Collection."""

    VERSION = 1

    async def async_step_user(
        self, info: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        data_schema = {
            vol.Required(CONF_ADDRESS): str,
        }

        if info is not None:
            result = None
            try:
                result = await validate_input(self.hass, info)
            except InvalidAddressError:
                return self.async_abort(reason="invalid_address")
            except Exception:  # pylint: disable=broad-except  # noqa: BLE001
                return self.async_abort(reason="unknown")
            else:
                return self.async_create_entry(
                    title="Peel Garable Collection Service",
                    data=result,
                )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))


class InvalidAddressError(HomeAssistantError):
    """Error to indicate the address is invalid."""
