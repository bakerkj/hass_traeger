"""
Custom integration to integrate traeger with Home Assistant.

For more details about this integration, please refer to
https://github.com/njobrien1006/hass_traeger
"""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import Config, Event, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS,
                    STARTUP_MESSAGE)
from .traeger import traeger

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):  # pylint: disable=unused-argument
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    session = async_get_clientsession(hass)

    client = traeger(username, password, hass, session)

    await client.start(30)
    hass.data[DOMAIN][entry.entry_id] = client

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform))

    async def async_shutdown(event: Event):  # pylint: disable=unused-argument
        """Shut down the client."""
        await client.kill()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(await asyncio.gather(*[
        hass.config_entries.async_forward_entry_unload(entry, platform)
        for platform in PLATFORMS
    ]))
    await client.kill()
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
