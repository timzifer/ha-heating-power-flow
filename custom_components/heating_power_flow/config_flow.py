"""Config flow for Heating Power Flow integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DENSITY,
    CONF_FLOW_A,
    CONF_FLOW_B,
    CONF_FLOW_SENSOR,
    CONF_MEDIUM,
    CONF_MODE,
    CONF_NAME,
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
    MEDIUM_EG_20,
    MEDIUM_EG_30,
    MEDIUM_EG_40,
    MEDIUM_PG_20,
    MEDIUM_PG_30,
    MEDIUM_PG_40,
    MEDIUM_WATER,
    MODE_SINK,
    MODE_SOURCE,
    TYPE_DUAL_LINE,
    TYPE_STANDARD,
    WATER_DENSITY_KG_L,
    WATER_SPECIFIC_HEAT_KJ,
)

ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

PUMP_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig()
)

PUMP_DELAY_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=300,
        step=1,
        unit_of_measurement="s",
        mode=selector.NumberSelectorMode.BOX,
    )
)

MEDIUM_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value=MEDIUM_WATER, label="Water / Wasser"),
            selector.SelectOptionDict(value=MEDIUM_EG_20, label="Ethylene Glycol 20%"),
            selector.SelectOptionDict(value=MEDIUM_EG_30, label="Ethylene Glycol 30%"),
            selector.SelectOptionDict(value=MEDIUM_EG_40, label="Ethylene Glycol 40%"),
            selector.SelectOptionDict(value=MEDIUM_PG_20, label="Propylene Glycol 20%"),
            selector.SelectOptionDict(value=MEDIUM_PG_30, label="Propylene Glycol 30%"),
            selector.SelectOptionDict(value=MEDIUM_PG_40, label="Propylene Glycol 40%"),
            selector.SelectOptionDict(value=MEDIUM_CUSTOM, label="Custom / Benutzerdefiniert"),
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

SPECIFIC_HEAT_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=1.0,
        max=10.0,
        step=0.001,
        unit_of_measurement="kJ/(kg·K)",
        mode=selector.NumberSelectorMode.BOX,
    )
)

DENSITY_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.5,
        max=2.0,
        step=0.001,
        unit_of_measurement="kg/L",
        mode=selector.NumberSelectorMode.BOX,
    )
)


class HeatingPowerFlowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Heating Power Flow."""

    VERSION = 4

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step: choose name, type, and medium."""
        if user_input is not None:
            self._data[CONF_NAME] = user_input[CONF_NAME]
            self._data[CONF_TYPE] = user_input[CONF_TYPE]
            self._data[CONF_MODE] = user_input[CONF_MODE]
            self._data[CONF_MEDIUM] = user_input[CONF_MEDIUM]

            if user_input[CONF_MEDIUM] == MEDIUM_CUSTOM:
                return await self.async_step_medium_custom()

            if user_input[CONF_TYPE] == TYPE_STANDARD:
                return await self.async_step_standard()
            return await self.async_step_dual_line()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_TYPE, default=TYPE_STANDARD): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=TYPE_STANDARD,
                                    label="Standard (Triplet)",
                                ),
                                selector.SelectOptionDict(
                                    value=TYPE_DUAL_LINE,
                                    label="Dual-Line (Special)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_MODE, default=MODE_SOURCE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MODE_SOURCE,
                                    label="Source (Heat producer)",
                                ),
                                selector.SelectOptionDict(
                                    value=MODE_SINK,
                                    label="Sink (Heat consumer)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_MEDIUM, default=MEDIUM_WATER): MEDIUM_SELECTOR,
                }
            ),
        )

    async def async_step_medium_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle custom medium properties input."""
        if user_input is not None:
            self._data[CONF_SPECIFIC_HEAT] = user_input[CONF_SPECIFIC_HEAT]
            self._data[CONF_DENSITY] = user_input[CONF_DENSITY]

            if self._data[CONF_TYPE] == TYPE_STANDARD:
                return await self.async_step_standard()
            return await self.async_step_dual_line()

        return self.async_show_form(
            step_id="medium_custom",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SPECIFIC_HEAT, default=WATER_SPECIFIC_HEAT_KJ
                    ): SPECIFIC_HEAT_SELECTOR,
                    vol.Required(
                        CONF_DENSITY, default=WATER_DENSITY_KG_L
                    ): DENSITY_SELECTOR,
                }
            ),
        )

    async def async_step_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the standard triplet configuration step."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
            )

        return self.async_show_form(
            step_id="standard",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FLOW_SENSOR): ENTITY_SELECTOR,
                    vol.Required(CONF_SUPPLY_TEMP): ENTITY_SELECTOR,
                    vol.Required(CONF_RETURN_TEMP): ENTITY_SELECTOR,
                    vol.Optional(CONF_PUMP_ENTITY): PUMP_ENTITY_SELECTOR,
                    vol.Optional(
                        CONF_PUMP_DELAY, default=DEFAULT_PUMP_DELAY
                    ): PUMP_DELAY_SELECTOR,
                }
            ),
        )

    async def async_step_dual_line(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the dual-line configuration step."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
            )

        return self.async_show_form(
            step_id="dual_line",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SUPPLY_TEMP_A): ENTITY_SELECTOR,
                    vol.Required(CONF_FLOW_A): ENTITY_SELECTOR,
                    vol.Required(CONF_SUPPLY_TEMP_B): ENTITY_SELECTOR,
                    vol.Required(CONF_FLOW_B): ENTITY_SELECTOR,
                    vol.Required(CONF_RETURN_TEMP): ENTITY_SELECTOR,
                    vol.Optional(CONF_PUMP_ENTITY): PUMP_ENTITY_SELECTOR,
                    vol.Optional(
                        CONF_PUMP_DELAY, default=DEFAULT_PUMP_DELAY
                    ): PUMP_DELAY_SELECTOR,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return HeatingPowerFlowOptionsFlow(config_entry)


class HeatingPowerFlowOptionsFlow(OptionsFlow):
    """Handle options flow for Heating Power Flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._options_data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle mode and medium selection as the first options step."""
        if user_input is not None:
            self._options_data[CONF_MODE] = user_input[CONF_MODE]
            self._options_data[CONF_MEDIUM] = user_input[CONF_MEDIUM]

            if user_input[CONF_MEDIUM] == MEDIUM_CUSTOM:
                return await self.async_step_medium_custom()

            if self._config_entry.data.get(CONF_TYPE) == TYPE_DUAL_LINE:
                return await self.async_step_dual_line()
            return await self.async_step_standard()

        current_mode = self._config_entry.data.get(CONF_MODE, MODE_SOURCE)
        current_medium = self._config_entry.data.get(CONF_MEDIUM, MEDIUM_WATER)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODE, default=current_mode
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MODE_SOURCE,
                                    label="Source (Heat producer)",
                                ),
                                selector.SelectOptionDict(
                                    value=MODE_SINK,
                                    label="Sink (Heat consumer)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_MEDIUM, default=current_medium
                    ): MEDIUM_SELECTOR,
                }
            ),
        )

    async def async_step_medium_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle custom medium properties input in options flow."""
        if user_input is not None:
            self._options_data[CONF_SPECIFIC_HEAT] = user_input[CONF_SPECIFIC_HEAT]
            self._options_data[CONF_DENSITY] = user_input[CONF_DENSITY]

            if self._config_entry.data.get(CONF_TYPE) == TYPE_DUAL_LINE:
                return await self.async_step_dual_line()
            return await self.async_step_standard()

        current_cp = self._config_entry.data.get(
            CONF_SPECIFIC_HEAT, WATER_SPECIFIC_HEAT_KJ
        )
        current_density = self._config_entry.data.get(
            CONF_DENSITY, WATER_DENSITY_KG_L
        )
        return self.async_show_form(
            step_id="medium_custom",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SPECIFIC_HEAT, default=current_cp
                    ): SPECIFIC_HEAT_SELECTOR,
                    vol.Required(
                        CONF_DENSITY, default=current_density
                    ): DENSITY_SELECTOR,
                }
            ),
        )

    async def async_step_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle options for standard triplet."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._options_data, **user_input}
            )

        current = self._config_entry.data
        pump_schema: dict[vol.Optional, Any] = {}
        current_pump = current.get(CONF_PUMP_ENTITY)
        if current_pump:
            pump_schema[vol.Optional(
                CONF_PUMP_ENTITY, default=current_pump
            )] = PUMP_ENTITY_SELECTOR
        else:
            pump_schema[vol.Optional(CONF_PUMP_ENTITY)] = PUMP_ENTITY_SELECTOR
        pump_schema[vol.Optional(
            CONF_PUMP_DELAY,
            default=current.get(CONF_PUMP_DELAY, DEFAULT_PUMP_DELAY),
        )] = PUMP_DELAY_SELECTOR

        return self.async_show_form(
            step_id="standard",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FLOW_SENSOR,
                        default=current.get(CONF_FLOW_SENSOR, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SUPPLY_TEMP,
                        default=current.get(CONF_SUPPLY_TEMP, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_RETURN_TEMP,
                        default=current.get(CONF_RETURN_TEMP, ""),
                    ): ENTITY_SELECTOR,
                    **pump_schema,
                }
            ),
        )

    async def async_step_dual_line(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle options for dual-line."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._options_data, **user_input}
            )

        current = self._config_entry.data
        pump_schema: dict[vol.Optional, Any] = {}
        current_pump = current.get(CONF_PUMP_ENTITY)
        if current_pump:
            pump_schema[vol.Optional(
                CONF_PUMP_ENTITY, default=current_pump
            )] = PUMP_ENTITY_SELECTOR
        else:
            pump_schema[vol.Optional(CONF_PUMP_ENTITY)] = PUMP_ENTITY_SELECTOR
        pump_schema[vol.Optional(
            CONF_PUMP_DELAY,
            default=current.get(CONF_PUMP_DELAY, DEFAULT_PUMP_DELAY),
        )] = PUMP_DELAY_SELECTOR

        return self.async_show_form(
            step_id="dual_line",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SUPPLY_TEMP_A,
                        default=current.get(CONF_SUPPLY_TEMP_A, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_FLOW_A,
                        default=current.get(CONF_FLOW_A, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SUPPLY_TEMP_B,
                        default=current.get(CONF_SUPPLY_TEMP_B, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_FLOW_B,
                        default=current.get(CONF_FLOW_B, ""),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_RETURN_TEMP,
                        default=current.get(CONF_RETURN_TEMP, ""),
                    ): ENTITY_SELECTOR,
                    **pump_schema,
                }
            ),
        )
