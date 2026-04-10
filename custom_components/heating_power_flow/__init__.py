"""The Heating Power Flow integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FLOW_A,
    CONF_FLOW_B,
    CONF_FLOW_SENSOR,
    CONF_RETURN_TEMP,
    CONF_SUPPLY_TEMP,
    CONF_SUPPLY_TEMP_A,
    CONF_SUPPLY_TEMP_B,
    CONF_TYPE,
    DOMAIN,
    PLATFORMS,
    TYPE_DUAL_LINE,
)
from .coordinator import DualLineFlowCoordinator, StandardFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heating Power Flow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config_type = entry.data.get(CONF_TYPE)

    if config_type == TYPE_DUAL_LINE:
        coordinator = DualLineFlowCoordinator(
            hass,
            flow_entity_a=entry.data[CONF_FLOW_A],
            supply_temp_entity_a=entry.data[CONF_SUPPLY_TEMP_A],
            flow_entity_b=entry.data[CONF_FLOW_B],
            supply_temp_entity_b=entry.data[CONF_SUPPLY_TEMP_B],
            return_temp_entity=entry.data[CONF_RETURN_TEMP],
        )
    else:
        coordinator = StandardFlowCoordinator(
            hass,
            flow_entity=entry.data[CONF_FLOW_SENSOR],
            supply_temp_entity=entry.data[CONF_SUPPLY_TEMP],
            return_temp_entity=entry.data[CONF_RETURN_TEMP],
        )

    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()

    return unload_ok
