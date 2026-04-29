"""API clients for Peel Garbage Collection integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_DEFAULT_TIMEOUT = 10
_DATE_TIME_FORMAT = "%Y-%m-%d"
_LOGGER = logging.getLogger(__name__)


class CollectionType(StrEnum):
    """Enum of all pickup types."""

    Garbage = "Garbage"
    Recycling = "Recycling"
    YardWaste = "Yard Waste"
    Organics = "Organics"
    GarbageExemption = "Garbage Exemption"
    Battery = "Battery"


class CollectionScheduleCalendarEntry:
    """Class representing a single calendar entry for garbage collection."""

    def __init__(self, date: str, types: list[CollectionType]) -> None:
        """Initialize the calendar entry."""
        self.date = datetime.strptime(date, _DATE_TIME_FORMAT)  # noqa: DTZ007
        self.types = types


class _BaseAPI:
    """Shared HTTP client base for collection APIs."""

    _API_ENDPOINT: str = ""
    _json_content_type: str | None = "application/json"

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._base_url = self._API_ENDPOINT.rstrip("/")
        self._timeout = ClientTimeout(total=timeout)
        self._session: ClientSession = async_get_clientsession(hass)

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Perform a GET request with retry logic."""
        url = f"{self._base_url}{endpoint}"
        retries = 2
        backoff = 0.5
        for attempt in range(retries + 1):
            try:
                async with self._session.get(
                    url, params=params, timeout=self._timeout
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=self._json_content_type)
            except (TimeoutError, ClientResponseError, ClientError) as err:
                _LOGGER.debug("GET %s failed (attempt %s): %s", url, attempt + 1, err)
                if attempt < retries:
                    await asyncio.sleep(backoff * (2**attempt))
                    continue
                _LOGGER.exception(
                    "Failed to GET %s after %s attempts.", url, attempt + 1
                )
                raise
        return None

    async def close(self) -> None:
        """No-op: session is managed by Home Assistant."""

    async def __aenter__(self) -> Any:
        """Async enter context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        """Async exit context manager."""
        await self.close()


class PeelRegionAPI(_BaseAPI):
    """API client for the Peel Region garbage collection service (ReCollect)."""

    _API_ENDPOINT = "https://api.recollect.net/api"

    async def search_address(self, address: str) -> dict | None:
        """Search for an address and return its details (first match)."""
        endpoint = "/areas/PeelRegionON/services/1063/address-suggest"
        params = {"q": address}

        data = await self._get(endpoint, params=params)
        if not data:
            _LOGGER.debug("No suggestions returned for '%s'", address)
            return None
        if isinstance(data, list) and data:
            return data[0]

        _LOGGER.warning(
            "Unexpected address suggest payload for '%s': %s", address, type(data)
        )
        return None

    async def get_collection_schedule(
        self, place_id: str, num_days: int = 30
    ) -> list[CollectionScheduleCalendarEntry] | None:
        """Retrieve the collection schedule starting today until num_days."""
        start_date = datetime.now(tz=UTC)
        end_date = start_date + timedelta(days=num_days)

        endpoint = f"/places/{place_id}/services/1063/events"
        params = {
            "after": start_date.strftime(_DATE_TIME_FORMAT),
            "before": end_date.strftime(_DATE_TIME_FORMAT),
            "locale": "en",
        }

        data = await self._get(endpoint, params=params)
        if not data:
            _LOGGER.error("Unable to retrieve collection schedule")
            return None

        if not isinstance(data, dict):
            _LOGGER.error("Invalid response format")
            return None

        events: list[dict] = data["events"]
        if not isinstance(events, list) or not events:
            _LOGGER.error("Events array is empty")
            return None

        calendar_entries: list[CollectionScheduleCalendarEntry] = []
        for event in events:
            if "type" in event and event["type"] == "holiday":
                continue
            calendar_entries.append(self._parse_event(event))

        return calendar_entries

    def _parse_event(self, event: dict) -> CollectionScheduleCalendarEntry:
        """Build a calendar entry from a ReCollect event response."""
        date = event["day"]
        types: list[CollectionType] = []

        for flag in event.get("flags", []):
            name = flag["name"]
            if name == "garbage":
                types.append(CollectionType.Garbage)
            elif name == "yardwaste":
                types.append(CollectionType.YardWaste)
            elif name == "organics":
                types.append(CollectionType.Organics)
            elif name == "garbage_exemption_day":
                types.append(CollectionType.GarbageExemption)
            elif name == "battery_pickup_day":
                types.append(CollectionType.Battery)

        return CollectionScheduleCalendarEntry(date, types)


_CIRCULAR_MATERIALS_PROJECTS = (
    "CIRCMAT:AIRDRIE,ALIX,BASHAW,BIRCHCLIFF,BLACKFALDS,BONACCORD,BOWISLAND,CALMAR,"
    "CARSTAIRS,CHAUVIN,CLIVE,CLYDE,CORONATION,DELBURNE,ELNORA,FAIRVIEW,"
    "FORTSASKATCHEWAN,GRANDPRAIRIE,GREENVIEWNO16,LEGAL,MAYERTHORPE,MEDICINEHAT,"
    "MORINVILLE,MUNDARE,OLDS,PARKLANDCOUNTY,PEACERIVER,PONOKA,SEXSMITH,TROCHU,"
    "VERMILION,WAINWRIGHT,WESTLOCK;"
    "CIRCMATNB:BAYSIDE,BEAVERHARBOUR,BLACKSHARBOUR,BONNYRIVER,CAMPOBELLO,CHAMCOOK,"
    "DEERISLAND,DENNISWESTON,DUFFERIN,DUMBARTON,FUNDYBAY,GRANDMANAN,LEPREAU,MCADAM,"
    "MUSQUASH,PENNFIELD,SAINTANDREWS,STCROIX,STDAVID,STGEORGE,STJAMES,STPATRICK,"
    "STSTEPHEN,STSTEPHENLSD,WESTERNCHARLOTTE;"
    "CIRCMATNS:ANTIGONISH,MFD,NOVASCOTIA,REGIONQUEENS,SCHOOLS,WAVESENDRVCG,YARMOUTH,"
    "YARMOUTHMUNI;"
    "CIRCMATONT:AJAX,ALGONQUINHIGHLANDS,AMARANTH,AMHERSTBURG,ARMOUR,ASPHODELNORWOOD,"
    "BARRIE,BRAMPTON,BRANT,BRIGHTON,BROCK,BROCKVILLE,CALEDON,CAMBRIDGE,CARLETONPLACE,"
    "CARLING,CAVANMONAGHAN,CHATHAMKENT,CLARENCEROCKLAND,CLARINGTON,COBOURG,"
    "DOURODUMMER,DYSARTETAL,EASTGARAFRAXA,ERIN,ESSEX,FORTERIE,GEORGIANBAY,"
    "GRANDVALLEY,GRIMSBY,GUELPHERAMOSA,HALDIMAND,HAVELOCKBELMONTMETHUEN,HUNTSVILLE,"
    "KINGSVILLE,KITCHENER,LINCOLN,LONDON,LUCANBIDDULPH,MALAHIDE,MAPLETON,MARKHAM,"
    "MELANCTHON,MINDENHILLS,MINTO,MISSISSAUGA,MISSISSIPPIMILLS,MONO,MULMUR,"
    "MUSKOKALAKES,NEWBURY,NIAGARAFALLS,NIAGARAONTHELAKE,NORFOLK,NORTHDUMFRIES,"
    "NORTHKAWARTHA,OTONABEESOUTHMONAGHAN,OTTAWA,PELHAM,PETERBOROUGH,PICKERING,"
    "PORTCOLBORNE,PORTHOPE,PUSLINCH,SARNIA,SCUGOG,SEGUIN,SELWYN,SHELBURNE,"
    "SOUTHGLENGARRY,SOUTHWOLD,STCATHARINES,TECUMSEH,TERACEBAY,THOROLD,TIMMINS,"
    "TORONTO,TRENTLAKES,UXBRIDGE,VAUGHAN,WAINFLEET,WATERLOO,WELLAND,WELLESLEY,"
    "WELLINGTONNORTH,WESTLINCOLN,WILMOT,WOOLWICH;"
    "CIRCMATYT:CARCROSS,CARMACKS,CHAMPAGNE,DAWSONCITY,DEEPCREEK,DESTRUCTIONBAY,FARO,"
    "HAINESJUNCTION,MARSHLAKE,MAYO,MOUNTLORNE,PELLYCROSSING,ROSSRIVER,TAGISH,TESLIN,"
    "WATSONLAKE,WHITEHORSE"
)


class CircularMaterialsAPI(_BaseAPI):
    """API client for the Circular Materials recycling schedule service."""

    _API_ENDPOINT = "https://ca-web.apigw.recyclecoach.com"
    _json_content_type = None  # API returns text/html despite sending JSON

    async def search_address(self, address: str) -> dict | None:
        """Search for an address and return district, project, and zone IDs."""
        endpoint = "/zone-setup/address/multi"
        params = {"term": address, "projects": _CIRCULAR_MATERIALS_PROJECTS}

        data = await self._get(endpoint, params=params)
        if not data or not data.get("success"):
            _LOGGER.debug("No suggestions returned for '%s'", address)
            return None

        results = data.get("results", [])
        if not results:
            _LOGGER.debug("Empty results for '%s'", address)
            return None

        result = results[0]
        zones: dict = result.get("zones", {})
        zone_id = next(iter(zones.values()), None)
        if not zone_id:
            _LOGGER.warning("No zone found in address response for '%s'", address)
            return None

        return {
            "district_id": result["district_id"],
            "project_id": result["project_id"],
            "zone_id": zone_id,
        }

    async def get_collection_schedule(
        self, project_id: str, district_id: str, zone_id: str, num_days: int = 30
    ) -> list[CollectionScheduleCalendarEntry] | None:
        """Retrieve the recycling schedule for the next num_days."""
        start_date = datetime.now(tz=UTC).date()
        end_date = start_date + timedelta(days=num_days)

        endpoint = "/zone-setup/zone/schedules"
        params = {
            "project_id": project_id,
            "district_id": district_id,
            "zone_id": f"zone-{zone_id}",
        }

        data = await self._get(endpoint, params=params)
        if not data:
            _LOGGER.error("Unable to retrieve recycling schedule")
            return None

        entries: list[CollectionScheduleCalendarEntry] = []
        for year_data in data.get("DATA", []):
            for month_data in year_data.get("months", []):
                for event in month_data.get("events", []):
                    collections: list[dict] = event.get("collections", [])
                    if any(c.get("status") == "is_none" for c in collections):
                        continue

                    event_date = datetime.strptime(  # noqa: DTZ007
                        event["date"], _DATE_TIME_FORMAT
                    ).date()
                    if not (start_date <= event_date < end_date):
                        continue

                    entries.append(
                        CollectionScheduleCalendarEntry(
                            event["date"], [CollectionType.Recycling]
                        )
                    )

        return entries
