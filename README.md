# Heating Power Flow

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that calculates thermal power (kW) and energy consumption (kWh) from existing flow and temperature sensors. Perfect for monitoring heat pumps, boilers, underfloor heating, and other hydronic heating/cooling systems.

## Features

- **Thermal power calculation** from flow rate and temperature difference
- **Separate heating & cooling energy counters** (Energy Dashboard compatible)
- **Two configuration modes:**
  - **Standard Triplet** - one flow sensor + supply & return temperature
  - **Dual-Line** - two supply lines with individual flow sensors sharing a common return temperature
- **Automatic unit conversion** (L/min, L/h, m³/h, gal/min)
- **Trapezoidal integration** for accurate energy calculation
- **Survives restarts** via state restoration
- **Full Config Flow UI** - no YAML configuration needed
- **German & English translations**

## Sensors Created

### Standard Triplet

| Sensor | Unit | Description |
|--------|------|-------------|
| Thermal Power | kW | Current heating (+) or cooling (-) power |
| Heating Energy | kWh | Accumulated heating energy (Energy Dashboard compatible) |
| Cooling Energy | kWh | Accumulated cooling energy (Energy Dashboard compatible) |
| Temperature Difference (ΔT) | °C | Supply temp - return temp |
| Flow Rate | L/min | Normalized flow rate |

### Dual-Line (Special)

| Sensor | Unit | Description |
|--------|------|-------------|
| Thermal Power A / B / Total | kW | Power per line and combined total |
| Heating Energy A / B / Total | kWh | Heating energy per line and total |
| Cooling Energy A / B / Total | kWh | Cooling energy per line and total |
| ΔT A / B | °C | Temperature difference per line |

## Formula

```
P(kW) = Flow(L/min) × ΔT(°C) × ρ × cp / 60

Where:
  ρ  = 1.0 kg/L      (water density)
  cp = 4.186 kJ/(kg·K) (specific heat capacity of water)

Simplified:
  P(kW) ≈ Flow(L/min) × ΔT(°C) × 0.06977
```

Energy is integrated using the trapezoidal rule:
```
ΔE(kWh) = (P_old + P_new) / 2 × Δt(h)
```

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/timzifer/ha-heating-power-flow` as **Integration**
4. Search for "Heating Power Flow" and install
5. Restart Home Assistant

### Manual

1. Download the latest release
2. Copy `custom_components/heating_power_flow/` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Heating Power Flow"**
3. Enter a name and choose the configuration type:

### Standard Triplet

Select three existing sensors:
- **Flow sensor** - volumetric flow rate (L/min, L/h, m³/h, or gal/min)
- **Supply temperature** (Vorlauf) - temperature of the outgoing water
- **Return temperature** (Rücklauf) - temperature of the returning water

### Dual-Line (Special)

Select five existing sensors for two supply lines sharing one return:
- **Supply temperature A** (Vorlauftemperatur A)
- **Flow sensor A** (Durchflusssensor Leitung A)
- **Supply temperature B** (Vorlauftemperatur B)
- **Flow sensor B** (Durchflusssensor Leitung B)
- **Common return temperature** (Gemeinsame Rücklauftemperatur)

## Energy Dashboard

The heating and cooling energy sensors use `SensorStateClass.TOTAL_INCREASING`, making them fully compatible with the Home Assistant Energy Dashboard.

1. Go to **Settings** → **Dashboards** → **Energy**
2. Add the heating/cooling energy sensors under **Gas consumption** or **Individual devices**

## Heating vs. Cooling

- **Positive ΔT** (supply > return) → Heating mode → Power is positive
- **Negative ΔT** (supply < return) → Cooling mode → Power is negative
- Heating energy accumulates only during heating (positive power)
- Cooling energy accumulates only during cooling (negative power, stored as positive value)

## Supported Flow Units

| Unit | Example |
|------|---------|
| L/min | 12.5 L/min |
| L/h | 750 L/h |
| m³/h | 0.75 m³/h |
| gal/min | 3.3 gal/min |

Units are automatically detected from the source sensor's `unit_of_measurement` attribute and converted to L/min internally.

---

# Deutsch

## Heating Power Flow - Heizleistungs-Durchfluss

Eine Home Assistant Custom Integration zur Berechnung der thermischen Leistung (kW) und des Energieverbrauchs (kWh) aus vorhandenen Durchfluss- und Temperatursensoren.

### Konfigurationstypen

**Standard-Triplet:**
- Durchflusssensor (L/min, m³/h, etc.)
- Vorlauftemperatur
- Rücklauftemperatur

**Dual-Line (Spezial):**
- Vorlauftemperatur A + Durchflusssensor A
- Vorlauftemperatur B + Durchflusssensor B
- Gemeinsame Rücklauftemperatur

### Erstellte Sensoren

- **Thermische Leistung** (kW) - positiv = Heizen, negativ = Kühlen
- **Heizenergie** (kWh) - akkumuliert nur bei positiver Leistung
- **Kühlenergie** (kWh) - akkumuliert nur bei negativer Leistung
- **Temperaturdifferenz ΔT** (°C) - Vorlauf minus Rücklauf
- **Durchflussrate** (L/min) - normalisierte Durchflussmenge

### Installation

1. HACS öffnen → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. `https://github.com/timzifer/ha-heating-power-flow` als **Integration** hinzufügen
3. "Heating Power Flow" suchen und installieren
4. Home Assistant neu starten

## License

MIT
