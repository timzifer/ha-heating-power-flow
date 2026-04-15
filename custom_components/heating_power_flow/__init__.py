"""The Heating Power Flow integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DENSITY,
    CONF_FLOW_A,
    CONF_FLOW_B,
    CONF_FLOW_SENSOR,
    CONF_MEDIUM,
    CONF_MODE,
    CONF_PUMP_DELAY,
    CONF_PUMP_ENTITY,
    CONF_RETURN_TEMP,
    CONF_SPECIFIC_HEAT,
    CONF_SUPPLY_TEMP,
    CONF_SUPPLY_TEMP_A,
    CONF_SUPPLY_TEMP_B,
    CONF_TYPE,
    DEFAULT_PUMP_DELAY,
    DOMAIN,
    MEDIUM_CUSTOM,
    MEDIUM_PRESETS,
    MEDIUM_WATER,
    MODE_SOURCE,
    PLATFORMS,
    TYPE_DUAL_LINE,
    WATER_DENSITY_KG_L,
    WATER_SPECIFIC_HEAT_KJ,
)
from .coordinator import DualLineFlowCoordinator, StandardFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data, CONF_MODE: MODE_SOURCE}
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )

    if config_entry.version == 2:
        # Pump fields are optional; existing entries simply won't have them.
        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data}, version=3
        )

    if config_entry.version == 3:
        # Add medium field defaulting to water for existing entries.
        new_data = {**config_entry.data, CONF_MEDIUM: MEDIUM_WATER}
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=4
        )

    _LOGGER.info("Migration to version %s successful", config_entry.version)
    return True


def _get_medium_properties(data: dict) -> tuple[float, float]:
    """Resolve medium config to (specific_heat, density)."""
    medium = data.get(CONF_MEDIUM, MEDIUM_WATER)
    if medium == MEDIUM_CUSTOM:
        return (
            data.get(CONF_SPECIFIC_HEAT, WATER_SPECIFIC_HEAT_KJ),
            data.get(CONF_DENSITY, WATER_DENSITY_KG_L),
        )
    cp, density = MEDIUM_PRESETS.get(medium, MEDIUM_PRESETS[MEDIUM_WATER])
    return cp, density


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heating Power Flow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config_type = entry.data.get(CONF_TYPE)
    pump_entity = entry.data.get(CONF_PUMP_ENTITY)
    pump_delay = entry.data.get(CONF_PUMP_DELAY, DEFAULT_PUMP_DELAY)
    specific_heat, density = _get_medium_properties(entry.data)

    if config_type == TYPE_DUAL_LINE:
        coordinator = DualLineFlowCoordinator(
            hass,
            flow_entity_a=entry.data[CONF_FLOW_A],
            supply_temp_entity_a=entry.data[CONF_SUPPLY_TEMP_A],
            flow_entity_b=entry.data[CONF_FLOW_B],
            supply_temp_entity_b=entry.data[CONF_SUPPLY_TEMP_B],
            return_temp_entity=entry.data[CONF_RETURN_TEMP],
            pump_entity=pump_entity,
            pump_delay=pump_delay,
            specific_heat=specific_heat,
            density=density,
        )
    else:
        coordinator = StandardFlowCoordinator(
            hass,
            flow_entity=entry.data[CONF_FLOW_SENSOR],
            supply_temp_entity=entry.data[CONF_SUPPLY_TEMP],
            return_temp_entity=entry.data[CONF_RETURN_TEMP],
            pump_entity=pump_entity,
            pump_delay=pump_delay,
            specific_heat=specific_heat,
            density=density,
        )

    coordinator.mode = entry.data.get(CONF_MODE, MODE_SOURCE)

    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update."""
    if entry.options:
        new_data = {**entry.data, **entry.options}
        # Remove optional keys that were explicitly cleared (set to None)
        for key in (CONF_PUMP_ENTITY,):
            if key in new_data and new_data[key] is None:
                del new_data[key]
        hass.config_entries.async_update_entry(entry, data=new_data, options={})
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()

    return unload_ok
