"""Calculation coordinator for Heating Power Flow integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    DEFAULT_EMA_ALPHA,
    FLOW_UNIT_CONVERSIONS,
    WATER_DENSITY_KG_L,
    WATER_SPECIFIC_HEAT_KJ,
)

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


class ExponentialMovingAverage:
    """Exponential Moving Average filter for sensor values."""

    def __init__(self, alpha: float = 1.0) -> None:
        """Initialize the EMA filter.

        Args:
            alpha: Smoothing factor (0..1]. 1.0 = no smoothing.
        """
        self._alpha = alpha
        self._value: float | None = None

    @property
    def enabled(self) -> bool:
        """Return True if smoothing is active (alpha < 1.0)."""
        return self._alpha < 1.0

    def update(self, value: float) -> float:
        """Feed a new raw value and return the smoothed result."""
        if self._value is None or not self.enabled:
            self._value = value
        else:
            self._value = self._alpha * value + (1.0 - self._alpha) * self._value
        return self._value

    def reset(self) -> None:
        """Clear internal state so the next update starts fresh."""
        self._value = None


def compute_power_factor(
    specific_heat: float = WATER_SPECIFIC_HEAT_KJ,
    density: float = WATER_DENSITY_KG_L,
) -> float:
    """Compute the power factor from medium properties.

    factor = ρ(kg/L) × cp(kJ/(kg·K)) / 60(s/min)
    """
    return density * specific_heat / 60.0


def calculate_power_kw(flow_l_min: float, delta_t: float, power_factor: float) -> float:
    """Calculate thermal power in kW.

    P(kW) = flow(L/min) × ΔT(K) × power_factor
    """
    return flow_l_min * delta_t * power_factor


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

    def reset_tracking(self) -> None:
        """Reset tracking state without losing accumulated energy."""
        self._last_power_kw = None
        self._last_update = None


class PumpGatingMixin:
    """Mixin adding pump state gating to a coordinator."""

    hass: HomeAssistant

    def _init_pump(
        self,
        pump_entity: str | None,
        pump_delay: int,
    ) -> None:
        """Initialize pump gating state."""
        self._pump_entity = pump_entity
        self._pump_delay = pump_delay
        self._pump_active: bool = False
        self._pump_raw_on: bool = False
        self._pump_delay_unsub: CALLBACK_TYPE | None = None
        self._pump_listeners: list[CALLBACK_TYPE] = []

    @property
    def pump_active(self) -> bool:
        """Return True if pump gating allows values, or if pump gating is disabled."""
        if self._pump_entity is None:
            return True
        return self._pump_active

    async def _async_start_pump_tracking(self) -> None:
        """Start listening to pump entity state changes."""
        if self._pump_entity is None:
            return
        self._pump_listeners.append(
            async_track_state_change_event(
                self.hass, [self._pump_entity], self._async_pump_state_changed
            )
        )
        self._check_initial_pump_state()

    def _check_initial_pump_state(self) -> None:
        """Check pump state at startup."""
        state = self.hass.states.get(self._pump_entity)
        if state is not None and state.state == "on":
            self._pump_raw_on = True
            self._start_pump_delay()
        else:
            self._pump_raw_on = False
            self._pump_active = False

    @callback
    def _async_pump_state_changed(self, event: Event) -> None:
        """Handle pump entity state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == "on":
            if not self._pump_raw_on:
                self._pump_raw_on = True
                self._start_pump_delay()
        else:
            self._pump_raw_on = False
            self._cancel_pump_delay()
            if self._pump_active:
                self._pump_active = False
                self._calculate()

    def _start_pump_delay(self) -> None:
        """Start the delay timer after pump turns on."""
        self._cancel_pump_delay()
        if self._pump_delay <= 0:
            self._pump_active = True
            self._calculate()
            return
        self._pump_delay_unsub = async_call_later(
            self.hass, self._pump_delay, self._pump_delay_elapsed
        )
        self._calculate()

    @callback
    def _pump_delay_elapsed(self, _now: Any) -> None:
        """Called when the pump delay timer expires."""
        self._pump_delay_unsub = None
        self._pump_active = True
        self._calculate()

    def _cancel_pump_delay(self) -> None:
        """Cancel any pending pump delay timer."""
        if self._pump_delay_unsub is not None:
            self._pump_delay_unsub()
            self._pump_delay_unsub = None

    async def _async_stop_pump_tracking(self) -> None:
        """Stop pump tracking and clean up."""
        self._cancel_pump_delay()
        for unsub in self._pump_listeners:
            unsub()
        self._pump_listeners.clear()

    def _calculate(self) -> None:
        """Must be implemented by the coordinator class."""
        raise NotImplementedError


class StandardFlowCoordinator(PumpGatingMixin):
    """Coordinator for a standard triplet (flow + supply temp + return temp)."""

    def __init__(
        self,
        hass: HomeAssistant,
        flow_entity: str,
        supply_temp_entity: str,
        return_temp_entity: str,
        pump_entity: str | None = None,
        pump_delay: int = 30,
        specific_heat: float = WATER_SPECIFIC_HEAT_KJ,
        density: float = WATER_DENSITY_KG_L,
        ema_alpha: float = DEFAULT_EMA_ALPHA,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.flow_entity = flow_entity
        self.supply_temp_entity = supply_temp_entity
        self.return_temp_entity = return_temp_entity

        self._power_factor = compute_power_factor(specific_heat, density)

        self.power_kw: float | None = None
        self.delta_t: float | None = None
        self.flow_rate_l_min: float | None = None
        self.energy = EnergyAccumulator()

        # Gated temperature passthrough values
        self.supply_temp_value: float | None = None
        self.return_temp_value: float | None = None

        # EMA filters for input sensors
        self._ema_flow = ExponentialMovingAverage(ema_alpha)
        self._ema_supply = ExponentialMovingAverage(ema_alpha)
        self._ema_return = ExponentialMovingAverage(ema_alpha)
        self._last_pump_active: bool | None = None

        self._listeners: list[Any] = []
        self._update_callbacks: list[callback] = []

        self._init_pump(pump_entity, pump_delay)

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
        await self._async_start_pump_tracking()
        self._calculate()

    async def async_stop(self) -> None:
        """Stop listening to state changes."""
        await self._async_stop_pump_tracking()
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Handle state changes from source entities."""
        self._calculate()

    def _reset_ema(self) -> None:
        """Reset all EMA filters."""
        self._ema_flow.reset()
        self._ema_supply.reset()
        self._ema_return.reset()

    def _calculate(self) -> None:
        """Recalculate all derived values."""
        flow_raw = _get_numeric_state(self.hass, self.flow_entity)
        supply_temp = _get_numeric_state(self.hass, self.supply_temp_entity)
        return_temp = _get_numeric_state(self.hass, self.return_temp_entity)

        if flow_raw is None or supply_temp is None or return_temp is None:
            self._reset_ema()
            self.power_kw = None
            self.delta_t = None
            self.flow_rate_l_min = None
            self.supply_temp_value = None
            self.return_temp_value = None
            self._notify()
            return

        # Reset EMA on pump state transitions to avoid stale trailing values
        if self._last_pump_active is not None and self.pump_active != self._last_pump_active:
            self._reset_ema()
        self._last_pump_active = self.pump_active

        # Apply EMA smoothing to raw sensor inputs
        flow_raw = self._ema_flow.update(flow_raw)
        supply_temp = self._ema_supply.update(supply_temp)
        return_temp = self._ema_return.update(return_temp)

        # Delta T and flow rate always pass through
        flow_unit = _get_flow_unit(self.hass, self.flow_entity)
        self.flow_rate_l_min = _convert_flow_to_l_min(flow_raw, flow_unit)
        self.delta_t = supply_temp - return_temp

        if self.pump_active:
            self.power_kw = calculate_power_kw(self.flow_rate_l_min, self.delta_t, self._power_factor)
            self.supply_temp_value = supply_temp
            self.return_temp_value = return_temp
            now = datetime.now(timezone.utc)
            self.energy.update(self.power_kw, now)
        else:
            self.power_kw = 0.0
            self.supply_temp_value = None
            self.return_temp_value = None
            self.energy.reset_tracking()

        self._notify()

    def _notify(self) -> None:
        """Notify all registered callbacks."""
        for cb in self._update_callbacks:
            cb()


class DualLineFlowCoordinator(PumpGatingMixin):
    """Coordinator for dual-line configuration (two supply lines, shared return)."""

    def __init__(
        self,
        hass: HomeAssistant,
        flow_entity_a: str,
        supply_temp_entity_a: str,
        flow_entity_b: str,
        supply_temp_entity_b: str,
        return_temp_entity: str,
        pump_entity: str | None = None,
        pump_delay: int = 30,
        specific_heat: float = WATER_SPECIFIC_HEAT_KJ,
        density: float = WATER_DENSITY_KG_L,
        ema_alpha: float = DEFAULT_EMA_ALPHA,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.flow_entity_a = flow_entity_a
        self.supply_temp_entity_a = supply_temp_entity_a
        self.flow_entity_b = flow_entity_b
        self.supply_temp_entity_b = supply_temp_entity_b
        self.return_temp_entity = return_temp_entity

        self._power_factor = compute_power_factor(specific_heat, density)

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

        # Gated temperature passthrough values
        self.supply_temp_a_value: float | None = None
        self.supply_temp_b_value: float | None = None
        self.return_temp_value: float | None = None

        # EMA filters for input sensors
        self._ema_flow_a = ExponentialMovingAverage(ema_alpha)
        self._ema_supply_a = ExponentialMovingAverage(ema_alpha)
        self._ema_flow_b = ExponentialMovingAverage(ema_alpha)
        self._ema_supply_b = ExponentialMovingAverage(ema_alpha)
        self._ema_return = ExponentialMovingAverage(ema_alpha)
        self._last_pump_active: bool | None = None

        self._listeners: list[Any] = []
        self._update_callbacks: list[callback] = []

        self._init_pump(pump_entity, pump_delay)

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
        await self._async_start_pump_tracking()
        self._calculate()

    async def async_stop(self) -> None:
        """Stop listening to state changes."""
        await self._async_stop_pump_tracking()
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Handle state changes from source entities."""
        self._calculate()

    def _reset_ema(self) -> None:
        """Reset all EMA filters."""
        self._ema_flow_a.reset()
        self._ema_supply_a.reset()
        self._ema_flow_b.reset()
        self._ema_supply_b.reset()
        self._ema_return.reset()

    def _calculate(self) -> None:
        """Recalculate all derived values."""
        return_temp = _get_numeric_state(self.hass, self.return_temp_entity)

        # Line A
        flow_a_raw = _get_numeric_state(self.hass, self.flow_entity_a)
        supply_a = _get_numeric_state(self.hass, self.supply_temp_entity_a)

        # Line B
        flow_b_raw = _get_numeric_state(self.hass, self.flow_entity_b)
        supply_b = _get_numeric_state(self.hass, self.supply_temp_entity_b)

        # Reset EMA on pump state transitions to avoid stale trailing values
        if self._last_pump_active is not None and self.pump_active != self._last_pump_active:
            self._reset_ema()
        self._last_pump_active = self.pump_active

        # Apply EMA to return temp (shared across lines)
        if return_temp is not None:
            return_temp = self._ema_return.update(return_temp)
        else:
            self._ema_return.reset()

        now = datetime.now(timezone.utc)
        power_a = None
        power_b = None

        # Calculate Line A
        if flow_a_raw is not None and supply_a is not None and return_temp is not None:
            flow_a_raw = self._ema_flow_a.update(flow_a_raw)
            supply_a = self._ema_supply_a.update(supply_a)
            flow_unit_a = _get_flow_unit(self.hass, self.flow_entity_a)
            flow_a_l_min = _convert_flow_to_l_min(flow_a_raw, flow_unit_a)
            self.delta_t_a = supply_a - return_temp
            if self.pump_active:
                power_a = calculate_power_kw(flow_a_l_min, self.delta_t_a, self._power_factor)
                self.power_a_kw = power_a
                self.energy_a.update(power_a, now)
            else:
                self.power_a_kw = 0.0
                self.energy_a.reset_tracking()
        else:
            self._ema_flow_a.reset()
            self._ema_supply_a.reset()
            self.power_a_kw = None
            self.delta_t_a = None

        # Calculate Line B
        if flow_b_raw is not None and supply_b is not None and return_temp is not None:
            flow_b_raw = self._ema_flow_b.update(flow_b_raw)
            supply_b = self._ema_supply_b.update(supply_b)
            flow_unit_b = _get_flow_unit(self.hass, self.flow_entity_b)
            flow_b_l_min = _convert_flow_to_l_min(flow_b_raw, flow_unit_b)
            self.delta_t_b = supply_b - return_temp
            if self.pump_active:
                power_b = calculate_power_kw(flow_b_l_min, self.delta_t_b, self._power_factor)
                self.power_b_kw = power_b
                self.energy_b.update(power_b, now)
            else:
                self.power_b_kw = 0.0
                self.energy_b.reset_tracking()
        else:
            self._ema_flow_b.reset()
            self._ema_supply_b.reset()
            self.power_b_kw = None
            self.delta_t_b = None

        # Total
        if self.pump_active:
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
        else:
            # At least one line has data (power_a_kw or power_b_kw is 0.0)
            if self.power_a_kw is not None or self.power_b_kw is not None:
                self.total_power_kw = 0.0
            else:
                self.total_power_kw = None
            self.total_energy.reset_tracking()

        # Gated temperature passthrough
        if self.pump_active:
            self.supply_temp_a_value = supply_a
            self.supply_temp_b_value = supply_b
            self.return_temp_value = return_temp
        else:
            self.supply_temp_a_value = None
            self.supply_temp_b_value = None
            self.return_temp_value = None

        self._notify()

    def _notify(self) -> None:
        """Notify all registered callbacks."""
        for cb in self._update_callbacks:
            cb()
