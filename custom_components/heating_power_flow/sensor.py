"""Sensor platform for Heating Power Flow integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_FLOW_A,
    CONF_FLOW_B,
    CONF_FLOW_SENSOR,
    CONF_MODE,
    CONF_NAME,
    CONF_RETURN_TEMP,
    CONF_SUPPLY_TEMP,
    CONF_SUPPLY_TEMP_A,
    CONF_SUPPLY_TEMP_B,
    CONF_TYPE,
    DOMAIN,
    MODE_SOURCE,
    TYPE_DUAL_LINE,
)
from .coordinator import (
    DualLineFlowCoordinator,
    StandardFlowCoordinator,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heating Power Flow sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]
    config_type = entry.data.get(CONF_TYPE)

    entities: list[SensorEntity] = []

    if config_type == TYPE_DUAL_LINE:
        entities = _create_dual_line_entities(coordinator, entry, name)
    else:
        entities = _create_standard_entities(coordinator, entry, name)

    async_add_entities(entities)


def _create_standard_entities(
    coordinator: StandardFlowCoordinator,
    entry: ConfigEntry,
    name: str,
) -> list[SensorEntity]:
    """Create sensor entities for a standard triplet configuration."""
    return [
        PowerSensor(coordinator, entry, name, "", "power_kw"),
        HeatingEnergySensor(coordinator, entry, name, "", "energy"),
        CoolingEnergySensor(coordinator, entry, name, "", "energy"),
        DeltaTSensor(coordinator, entry, name, "", "delta_t"),
        FlowRateSensor(coordinator, entry, name),
        CircuitModeSensor(coordinator, entry, name),
    ]


def _create_dual_line_entities(
    coordinator: DualLineFlowCoordinator,
    entry: ConfigEntry,
    name: str,
) -> list[SensorEntity]:
    """Create sensor entities for a dual-line configuration."""
    return [
        # Line A
        DualLinePowerSensor(coordinator, entry, name, "A", "power_a_kw"),
        DualLineHeatingEnergySensor(coordinator, entry, name, "A", "energy_a"),
        DualLineCoolingEnergySensor(coordinator, entry, name, "A", "energy_a"),
        DualLineDeltaTSensor(coordinator, entry, name, "A", "delta_t_a"),
        # Line B
        DualLinePowerSensor(coordinator, entry, name, "B", "power_b_kw"),
        DualLineHeatingEnergySensor(coordinator, entry, name, "B", "energy_b"),
        DualLineCoolingEnergySensor(coordinator, entry, name, "B", "energy_b"),
        DualLineDeltaTSensor(coordinator, entry, name, "B", "delta_t_b"),
        # Totals
        DualLinePowerSensor(coordinator, entry, name, "Total", "total_power_kw"),
        DualLineHeatingEnergySensor(
            coordinator, entry, name, "Total", "total_energy"
        ),
        DualLineCoolingEnergySensor(
            coordinator, entry, name, "Total", "total_energy"
        ),
        CircuitModeSensor(coordinator, entry, name),
    ]


class HeatingPowerFlowBaseSensor(SensorEntity):
    """Base class for all Heating Power Flow sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: StandardFlowCoordinator | DualLineFlowCoordinator,
        entry: ConfigEntry,
        base_name: str,
    ) -> None:
        """Initialize the base sensor."""
        self._coordinator = coordinator
        config_type_label = (
            entry.data.get(CONF_TYPE, "standard").replace("_", " ").title()
        )
        mode_label = entry.data.get(CONF_MODE, MODE_SOURCE).title()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=base_name,
            manufacturer="Heating Power Flow",
            model=f"{config_type_label} ({mode_label})",
            entry_type=DeviceEntryType.SERVICE,
        )


# =============================================================================
# Standard Triplet Sensors
# =============================================================================


class PowerSensor(HeatingPowerFlowBaseSensor):
    """Thermal power sensor (kW) for standard triplet."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        suffix: str,
        attr: str,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_name = "Thermal Power"
        self._attr = attr

    @property
    def native_value(self) -> float | None:
        """Return the current power value."""
        return self._coordinator.power_kw

    async def async_added_to_hass(self) -> None:
        """Register callback when added to hass."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class HeatingEnergySensor(HeatingPowerFlowBaseSensor, RestoreEntity):
    """Heating energy sensor (kWh) for standard triplet."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:fire"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        suffix: str,
        attr: str,
    ) -> None:
        """Initialize the heating energy sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_heating_energy"
        self._attr_name = "Heating Energy"

    @property
    def native_value(self) -> float | None:
        """Return the accumulated heating energy."""
        return self._coordinator.energy.heating_energy_kwh

    async def async_added_to_hass(self) -> None:
        """Restore state and register callback."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unavailable",
            "unknown",
        ):
            try:
                restored = float(last_state.state)
                self._coordinator.energy.restore(
                    restored,
                    self._coordinator.energy.cooling_energy_kwh,
                )
            except (ValueError, TypeError):
                pass
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class CoolingEnergySensor(HeatingPowerFlowBaseSensor, RestoreEntity):
    """Cooling energy sensor (kWh) for standard triplet."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:snowflake"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        suffix: str,
        attr: str,
    ) -> None:
        """Initialize the cooling energy sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_cooling_energy"
        self._attr_name = "Cooling Energy"

    @property
    def native_value(self) -> float | None:
        """Return the accumulated cooling energy."""
        return self._coordinator.energy.cooling_energy_kwh

    async def async_added_to_hass(self) -> None:
        """Restore state and register callback."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unavailable",
            "unknown",
        ):
            try:
                restored = float(last_state.state)
                self._coordinator.energy.restore(
                    self._coordinator.energy.heating_energy_kwh,
                    restored,
                )
            except (ValueError, TypeError):
                pass
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class DeltaTSensor(HeatingPowerFlowBaseSensor):
    """Temperature difference sensor (ΔT) for standard triplet."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:thermometer-lines"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        suffix: str,
        attr: str,
    ) -> None:
        """Initialize the delta T sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_delta_t"
        self._attr_name = "Temperature Difference (ΔT)"

    @property
    def native_value(self) -> float | None:
        """Return the temperature difference."""
        return self._coordinator.delta_t

    async def async_added_to_hass(self) -> None:
        """Register callback when added to hass."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class FlowRateSensor(HeatingPowerFlowBaseSensor):
    """Normalized flow rate sensor (L/min) for standard triplet."""

    _attr_native_unit_of_measurement = "L/min"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:water-pump"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize the flow rate sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_flow_rate"
        self._attr_name = "Flow Rate"

    @property
    def native_value(self) -> float | None:
        """Return the normalized flow rate in L/min."""
        return self._coordinator.flow_rate_l_min

    async def async_added_to_hass(self) -> None:
        """Register callback when added to hass."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class CircuitModeSensor(HeatingPowerFlowBaseSensor):
    """Diagnostic sensor exposing the circuit mode (source/sink)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:swap-vertical"

    def __init__(
        self,
        coordinator: StandardFlowCoordinator | DualLineFlowCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize the circuit mode sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_circuit_mode"
        self._attr_name = "Circuit Mode"
        self._mode = entry.data.get(CONF_MODE, MODE_SOURCE)

    @property
    def native_value(self) -> str:
        """Return the circuit mode."""
        return self._mode


# =============================================================================
# Dual-Line Sensors
# =============================================================================


class DualLinePowerSensor(HeatingPowerFlowBaseSensor):
    """Power sensor for dual-line configuration."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        coordinator: DualLineFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        line: str,
        attr: str,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_power_{line.lower()}"
        self._attr_name = f"Thermal Power {line}"
        self._power_attr = attr

    @property
    def native_value(self) -> float | None:
        """Return the current power value."""
        return getattr(self._coordinator, self._power_attr, None)

    async def async_added_to_hass(self) -> None:
        """Register callback when added to hass."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class DualLineHeatingEnergySensor(HeatingPowerFlowBaseSensor, RestoreEntity):
    """Heating energy sensor for dual-line configuration."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:fire"

    def __init__(
        self,
        coordinator: DualLineFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        line: str,
        energy_attr: str,
    ) -> None:
        """Initialize the heating energy sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_heating_energy_{line.lower()}"
        self._attr_name = f"Heating Energy {line}"
        self._energy_attr = energy_attr

    @property
    def native_value(self) -> float | None:
        """Return the accumulated heating energy."""
        accumulator = getattr(self._coordinator, self._energy_attr, None)
        if accumulator is None:
            return None
        return accumulator.heating_energy_kwh

    async def async_added_to_hass(self) -> None:
        """Restore state and register callback."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unavailable",
            "unknown",
        ):
            try:
                restored = float(last_state.state)
                accumulator = getattr(self._coordinator, self._energy_attr, None)
                if accumulator is not None:
                    accumulator.restore(restored, accumulator.cooling_energy_kwh)
            except (ValueError, TypeError):
                pass
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class DualLineCoolingEnergySensor(HeatingPowerFlowBaseSensor, RestoreEntity):
    """Cooling energy sensor for dual-line configuration."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:snowflake"

    def __init__(
        self,
        coordinator: DualLineFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        line: str,
        energy_attr: str,
    ) -> None:
        """Initialize the cooling energy sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_cooling_energy_{line.lower()}"
        self._attr_name = f"Cooling Energy {line}"
        self._energy_attr = energy_attr

    @property
    def native_value(self) -> float | None:
        """Return the accumulated cooling energy."""
        accumulator = getattr(self._coordinator, self._energy_attr, None)
        if accumulator is None:
            return None
        return accumulator.cooling_energy_kwh

    async def async_added_to_hass(self) -> None:
        """Restore state and register callback."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unavailable",
            "unknown",
        ):
            try:
                restored = float(last_state.state)
                accumulator = getattr(self._coordinator, self._energy_attr, None)
                if accumulator is not None:
                    accumulator.restore(accumulator.heating_energy_kwh, restored)
            except (ValueError, TypeError):
                pass
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class DualLineDeltaTSensor(HeatingPowerFlowBaseSensor):
    """Temperature difference sensor for dual-line configuration."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:thermometer-lines"

    def __init__(
        self,
        coordinator: DualLineFlowCoordinator,
        entry: ConfigEntry,
        name: str,
        line: str,
        attr: str,
    ) -> None:
        """Initialize the delta T sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_delta_t_{line.lower()}"
        self._attr_name = f"Temperature Difference (ΔT) {line}"
        self._delta_attr = attr

    @property
    def native_value(self) -> float | None:
        """Return the temperature difference."""
        return getattr(self._coordinator, self._delta_attr, None)

    async def async_added_to_hass(self) -> None:
        """Register callback when added to hass."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when removed from hass."""
        self._coordinator.remove_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()
