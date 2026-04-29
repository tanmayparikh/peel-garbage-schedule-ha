"""Config flow for Peel Garbage Collection integration."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

from .api import CircularMaterialsAPI, PeelRegionAPI
from .const import (
    CONF_ADDRESS,
    CONF_CIRCULAR_DISTRICT_ID,
    CONF_CIRCULAR_PROJECT_ID,
    CONF_CIRCULAR_ZONE_ID,
    CONF_PEEL_PLACE_ID,
    CONF_PEEL_TITLE,
    DOMAIN,
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    address = data[CONF_ADDRESS].strip()
    if not address:
        raise InvalidAddressError(
            translation_domain=DOMAIN,
            translation_key="error.empty_address",
        )

    peel_api = PeelRegionAPI(hass)
    circular_api = CircularMaterialsAPI(hass)

    peel_result, circular_result = await asyncio.gather(
        peel_api.search_address(address),
        circular_api.search_address(address),
    )

    if not peel_result:
        raise InvalidAddressError(
            translation_domain=DOMAIN,
            translation_key="error.invalid_address",
        )

    if not circular_result:
        raise InvalidAddressError(
            translation_domain=DOMAIN,
            translation_key="error.invalid_address",
        )

    return {
        CONF_PEEL_TITLE: peel_result["name"],
        CONF_PEEL_PLACE_ID: peel_result["place_id"],
        CONF_CIRCULAR_DISTRICT_ID: circular_result["district_id"],
        CONF_CIRCULAR_PROJECT_ID: circular_result["project_id"],
        CONF_CIRCULAR_ZONE_ID: circular_result["zone_id"],
    }


class AddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Peel Garbage Collection."""

    VERSION = 2

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
            except Exception as err:  # pylint: disable=broad-except  # noqa: BLE001
                return self.async_abort(reason=str(err))
            else:
                return self.async_create_entry(
                    title="Peel Garbage Collection Service",
                    data=result,
                )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))


class InvalidAddressError(HomeAssistantError):
    """Error to indicate the address is invalid."""
