"""Constants for the Heating Power Flow integration."""

DOMAIN = "heating_power_flow"
PLATFORMS = ["sensor"]

# Configuration types
CONF_TYPE = "config_type"
TYPE_STANDARD = "standard"
TYPE_DUAL_LINE = "dual_line"

# Circuit mode
CONF_MODE = "mode"
MODE_SOURCE = "source"
MODE_SINK = "sink"

# Pump entity configuration
CONF_PUMP_ENTITY = "pump_entity"
CONF_PUMP_DELAY = "pump_delay"
DEFAULT_PUMP_DELAY = 30  # seconds

# Medium configuration
CONF_MEDIUM = "medium"
CONF_SPECIFIC_HEAT = "specific_heat"
CONF_DENSITY = "density"

# Medium preset keys
MEDIUM_WATER = "water"
MEDIUM_EG_20 = "ethylene_glycol_20"
MEDIUM_EG_30 = "ethylene_glycol_30"
MEDIUM_EG_40 = "ethylene_glycol_40"
MEDIUM_PG_20 = "propylene_glycol_20"
MEDIUM_PG_30 = "propylene_glycol_30"
MEDIUM_PG_40 = "propylene_glycol_40"
MEDIUM_CUSTOM = "custom"

# Medium presets: (specific_heat kJ/(kg·K), density kg/L) at ~40 °C
MEDIUM_PRESETS: dict[str, tuple[float, float]] = {
    MEDIUM_WATER: (4.186, 1.0),
    MEDIUM_EG_20: (3.86, 1.025),
    MEDIUM_EG_30: (3.56, 1.040),
    MEDIUM_EG_40: (3.26, 1.054),
    MEDIUM_PG_20: (3.92, 1.017),
    MEDIUM_PG_30: (3.68, 1.026),
    MEDIUM_PG_40: (3.43, 1.034),
}

# Standard triplet config keys
CONF_NAME = "name"
CONF_FLOW_SENSOR = "flow_sensor"
CONF_SUPPLY_TEMP = "supply_temp"
CONF_RETURN_TEMP = "return_temp"

# Dual-line config keys
CONF_FLOW_A = "flow_sensor_a"
CONF_SUPPLY_TEMP_A = "supply_temp_a"
CONF_FLOW_B = "flow_sensor_b"
CONF_SUPPLY_TEMP_B = "supply_temp_b"
# CONF_RETURN_TEMP is shared

# Default physics constants (water)
WATER_SPECIFIC_HEAT_KJ = 4.186  # kJ/(kg·K)
WATER_DENSITY_KG_L = 1.0  # kg/L (approximation at ~20-60°C)

# Flow unit conversion factors (to L/min)
FLOW_UNIT_CONVERSIONS: dict[str, float] = {
    "L/min": 1.0,
    "l/min": 1.0,
    "L/h": 1.0 / 60.0,
    "l/h": 1.0 / 60.0,
    "m³/h": 1000.0 / 60.0,
    "m³/min": 1000.0,
    "gal/min": 3.78541,
    "gpm": 3.78541,
}

# Sensor keys
SENSOR_POWER = "power"
SENSOR_HEATING_ENERGY = "heating_energy"
SENSOR_COOLING_ENERGY = "cooling_energy"
SENSOR_DELTA_T = "delta_t"
SENSOR_FLOW_RATE = "flow_rate"

# Dual-line sensor suffixes
SENSOR_POWER_A = "power_a"
SENSOR_POWER_B = "power_b"
SENSOR_TOTAL_POWER = "total_power"
SENSOR_HEATING_ENERGY_A = "heating_energy_a"
SENSOR_COOLING_ENERGY_A = "cooling_energy_a"
SENSOR_HEATING_ENERGY_B = "heating_energy_b"
SENSOR_COOLING_ENERGY_B = "cooling_energy_b"
SENSOR_TOTAL_HEATING_ENERGY = "total_heating_energy"
SENSOR_TOTAL_COOLING_ENERGY = "total_cooling_energy"
SENSOR_DELTA_T_A = "delta_t_a"
SENSOR_DELTA_T_B = "delta_t_b"
