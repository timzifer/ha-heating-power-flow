"""Config flow for Heating Power Flow integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    MODE_SINK,
    MODE_SOURCE,
    TYPE_DUAL_LINE,
    TYPE_STANDARD,
)

ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)


class HeatingPowerFlowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Heating Power Flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step: choose name and type."""
        if user_input is not None:
            self._data[CONF_NAME] = user_input[CONF_NAME]
            self._data[CONF_TYPE] = user_input[CONF_TYPE]
            self._data[CONF_MODE] = user_input[CONF_MODE]

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
        """Handle mode selection as the first options step."""
        if user_input is not None:
            self._options_data[CONF_MODE] = user_input[CONF_MODE]
            if self._config_entry.data.get(CONF_TYPE) == TYPE_DUAL_LINE:
                return await self.async_step_dual_line()
            return await self.async_step_standard()

        current_mode = self._config_entry.data.get(CONF_MODE, MODE_SOURCE)
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
                }
            ),
        )
