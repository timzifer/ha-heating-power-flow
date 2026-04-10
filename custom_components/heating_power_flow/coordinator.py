"""Calculation coordinator for Heating Power Flow integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import FLOW_UNIT_CONVERSIONS, POWER_FACTOR_L_MIN

_LOGGER = logging.getLogger(__name__)


def _get_numeric_state(hass: HomeAssistant, entity_id: str) -> float | None:
    """Get the numeric state of an entity, returning None if unavailable."""
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None


def _get_flow_unit(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get the unit of measurement for a flow sensor."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return state.attributes.get("unit_of_measurement")


def _convert_flow_to_l_min(flow_value: float, unit: str | None) -> float:
    """Convert a flow value to L/min."""
    if unit is None:
        return flow_value
    factor = FLOW_UNIT_CONVERSIONS.get(unit, 1.0)
    return flow_value * factor


def calculate_power_kw(flow_l_min: float, delta_t: float) -> float:
    """Calculate thermal power in kW.

    P(kW) = flow(L/min) × ΔT(K) × ρ(kg/L) × cp(kJ/(kg·K)) / 60(s/min)
    """
    return flow_l_min * delta_t * POWER_FACTOR_L_MIN


class EnergyAccumulator:
    """Accumulates energy using the trapezoidal rule."""

    def __init__(self) -> None:
        """Initialize the accumulator."""
        self.heating_energy_kwh: float = 0.0
        self.cooling_energy_kwh: float = 0.0
        self._last_power_kw: float | None = None
        self._last_update: datetime | None = None

    def restore(self, heating_kwh: float, cooling_kwh: float) -> None:
        """Restore energy values from persistent storage."""
        self.heating_energy_kwh = heating_kwh
        self.cooling_energy_kwh = cooling_kwh

    def update(self, power_kw: float, now: datetime) -> None:
        """Update energy accumulation using trapezoidal integration."""
        if self._last_power_kw is not None and self._last_update is not None:
            dt_hours = (now - self._last_update).total_seconds() / 3600.0

            if dt_hours > 0 and dt_hours < 1.0:
                avg_power = (self._last_power_kw + power_kw) / 2.0
                energy_delta = avg_power * dt_hours

                if energy_delta > 0:
                    self.heating_energy_kwh += energy_delta
                elif energy_delta < 0:
                    self.cooling_energy_kwh += abs(energy_delta)

        self._last_power_kw = power_kw
        self._last_update = now


class StandardFlowCoordinator:
    """Coordinator for a standard triplet (flow + supply temp + return temp)."""

    def __init__(
        self,
        hass: HomeAssistant,
        flow_entity: str,
        supply_temp_entity: str,
        return_temp_entity: str,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.flow_entity = flow_entity
        self.supply_temp_entity = supply_temp_entity
        self.return_temp_entity = return_temp_entity

        self.power_kw: float | None = None
        self.delta_t: float | None = None
        self.flow_rate_l_min: float | None = None
        self.energy = EnergyAccumulator()

        self._listeners: list[Any] = []
        self._update_callbacks: list[callback] = []

    def register_callback(self, cb: callback) -> None:
        """Register a callback for state updates."""
        self._update_callbacks.append(cb)

    def remove_callback(self, cb: callback) -> None:
        """Remove a registered callback."""
        self._update_callbacks.remove(cb)

    async def async_start(self) -> None:
        """Start listening to source entity state changes."""
        entities = [
            self.flow_entity,
            self.supply_temp_entity,
            self.return_temp_entity,
        ]
        self._listeners.append(
            async_track_state_change_event(
                self.hass, entities, self._async_state_changed
            )
        )
        self._calculate()

    async def async_stop(self) -> None:
        """Stop listening to state changes."""
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Handle state changes from source entities."""
        self._calculate()

    def _calculate(self) -> None:
        """Recalculate all derived values."""
        flow_raw = _get_numeric_state(self.hass, self.flow_entity)
        supply_temp = _get_numeric_state(self.hass, self.supply_temp_entity)
        return_temp = _get_numeric_state(self.hass, self.return_temp_entity)

        if flow_raw is None or supply_temp is None or return_temp is None:
            self.power_kw = None
            self.delta_t = None
            self.flow_rate_l_min = None
            self._notify()
            return

        flow_unit = _get_flow_unit(self.hass, self.flow_entity)
        self.flow_rate_l_min = _convert_flow_to_l_min(flow_raw, flow_unit)
        self.delta_t = supply_temp - return_temp
        self.power_kw = calculate_power_kw(self.flow_rate_l_min, self.delta_t)

        now = datetime.now(timezone.utc)
        self.energy.update(self.power_kw, now)

        self._notify()

    def _notify(self) -> None:
        """Notify all registered callbacks."""
        for cb in self._update_callbacks:
            cb()


class DualLineFlowCoordinator:
    """Coordinator for dual-line configuration (two supply lines, shared return)."""

    def __init__(
        self,
        hass: HomeAssistant,
        flow_entity_a: str,
        supply_temp_entity_a: str,
        flow_entity_b: str,
        supply_temp_entity_b: str,
        return_temp_entity: str,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.flow_entity_a = flow_entity_a
        self.supply_temp_entity_a = supply_temp_entity_a
        self.flow_entity_b = flow_entity_b
        self.supply_temp_entity_b = supply_temp_entity_b
        self.return_temp_entity = return_temp_entity

        # Line A values
        self.power_a_kw: float | None = None
        self.delta_t_a: float | None = None
        self.energy_a = EnergyAccumulator()

        # Line B values
        self.power_b_kw: float | None = None
        self.delta_t_b: float | None = None
        self.energy_b = EnergyAccumulator()

        # Total values
        self.total_power_kw: float | None = None
        self.total_energy = EnergyAccumulator()

        self._listeners: list[Any] = []
        self._update_callbacks: list[callback] = []

    def register_callback(self, cb: callback) -> None:
        """Register a callback for state updates."""
        self._update_callbacks.append(cb)

    def remove_callback(self, cb: callback) -> None:
        """Remove a registered callback."""
        self._update_callbacks.remove(cb)

    async def async_start(self) -> None:
        """Start listening to source entity state changes."""
        entities = [
            self.flow_entity_a,
            self.supply_temp_entity_a,
            self.flow_entity_b,
            self.supply_temp_entity_b,
            self.return_temp_entity,
        ]
        self._listeners.append(
            async_track_state_change_event(
                self.hass, entities, self._async_state_changed
            )
        )
        self._calculate()

    async def async_stop(self) -> None:
        """Stop listening to state changes."""
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Handle state changes from source entities."""
        self._calculate()

    def _calculate(self) -> None:
        """Recalculate all derived values."""
        return_temp = _get_numeric_state(self.hass, self.return_temp_entity)

        # Line A
        flow_a_raw = _get_numeric_state(self.hass, self.flow_entity_a)
        supply_a = _get_numeric_state(self.hass, self.supply_temp_entity_a)

        # Line B
        flow_b_raw = _get_numeric_state(self.hass, self.flow_entity_b)
        supply_b = _get_numeric_state(self.hass, self.supply_temp_entity_b)

        now = datetime.now(timezone.utc)
        power_a = None
        power_b = None

        # Calculate Line A
        if flow_a_raw is not None and supply_a is not None and return_temp is not None:
            flow_unit_a = _get_flow_unit(self.hass, self.flow_entity_a)
            flow_a_l_min = _convert_flow_to_l_min(flow_a_raw, flow_unit_a)
            self.delta_t_a = supply_a - return_temp
            power_a = calculate_power_kw(flow_a_l_min, self.delta_t_a)
            self.power_a_kw = power_a
            self.energy_a.update(power_a, now)
        else:
            self.power_a_kw = None
            self.delta_t_a = None

        # Calculate Line B
        if flow_b_raw is not None and supply_b is not None and return_temp is not None:
            flow_unit_b = _get_flow_unit(self.hass, self.flow_entity_b)
            flow_b_l_min = _convert_flow_to_l_min(flow_b_raw, flow_unit_b)
            self.delta_t_b = supply_b - return_temp
            power_b = calculate_power_kw(flow_b_l_min, self.delta_t_b)
            self.power_b_kw = power_b
            self.energy_b.update(power_b, now)
        else:
            self.power_b_kw = None
            self.delta_t_b = None

        # Total
        if power_a is not None and power_b is not None:
            self.total_power_kw = power_a + power_b
            self.total_energy.update(self.total_power_kw, now)
        elif power_a is not None:
            self.total_power_kw = power_a
            self.total_energy.update(self.total_power_kw, now)
        elif power_b is not None:
            self.total_power_kw = power_b
            self.total_energy.update(self.total_power_kw, now)
        else:
            self.total_power_kw = None

        self._notify()

    def _notify(self) -> None:
        """Notify all registered callbacks."""
        for cb in self._update_callbacks:
            cb()
