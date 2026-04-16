# Heating Power Flow

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that calculates thermal power (kW) and energy consumption (kWh) from existing flow and temperature sensors. Perfect for monitoring heat pumps, boilers, underfloor heating, and other hydronic heating/cooling systems.

## Features

- **Thermal power calculation** from flow rate and temperature difference
- **Separate heating & cooling energy counters** (Energy Dashboard compatible)
- **System energy sensor** with net balance (heating - cooling)
- **Circuit mode** - Source (heat producer) or Sink (heat consumer) with sign-adjusted system power
- **Two configuration modes:**
  - **Standard Triplet** - one flow sensor + supply & return temperature
  - **Dual-Line** - two supply lines with individual flow sensors sharing a common return temperature
- **Medium selection** - Water, Ethylene/Propylene Glycol mixtures (20/30/40%), or custom fluid properties
- **Pump gating** - optional pump entity with configurable delay to suppress invalid readings during startup
- **EMA smoothing** - optional Exponential Moving Average filter on input sensors for noise reduction
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
| System Power | kW | Sign-adjusted power (positive = energy delivered in configured direction) |
| Heating Energy | kWh | Accumulated heating energy (Energy Dashboard compatible) |
| Cooling Energy | kWh | Accumulated cooling energy (Energy Dashboard compatible) |
| System Energy | kWh | Net energy balance (heating - cooling) |
| Temperature Difference (ΔT) | °C | Supply temp - return temp |
| Flow Rate | L/min | Normalized flow rate |
| Circuit Mode | - | Diagnostic: shows current mode (source/sink) |

When a pump entity is configured, additional gated temperature sensors are created:

| Sensor | Unit | Description |
|--------|------|-------------|
| Supply Temperature | °C | Supply temp (only available when pump is active) |
| Return Temperature | °C | Return temp (only available when pump is active) |

### Dual-Line (Special)

| Sensor | Unit | Description |
|--------|------|-------------|
| Thermal Power A / B / Total | kW | Power per line and combined total |
| System Power | kW | Sign-adjusted total power |
| Heating Energy A / B / Total | kWh | Heating energy per line and total |
| Cooling Energy A / B / Total | kWh | Cooling energy per line and total |
| System Energy A / B / Total | kWh | Net energy balance per line and total |
| ΔT A / B | °C | Temperature difference per line |
| Circuit Mode | - | Diagnostic: shows current mode (source/sink) |

When a pump entity is configured, additional gated temperature sensors are created for Supply A, Supply B, and Return.

## Formula

```
P(kW) = Flow(L/min) × ΔT(°C) × ρ × cp / 60

Where:
  ρ  = density in kg/L       (water: 1.0)
  cp = specific heat in kJ/(kg·K) (water: 4.186)

Example for water:
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
3. Enter a name and choose the configuration type

### Step 1: General Settings

| Setting | Description |
|---------|-------------|
| **Name** | Name for this energy flow monitor |
| **Configuration type** | Standard (Triplet) or Dual-Line (Special) |
| **Circuit mode** | Source (heat producer, e.g. heat pump) or Sink (heat consumer, e.g. floor heating) |
| **Heat transfer medium** | Water, Glycol mixtures, or Custom (enter specific heat & density manually) |

### Step 2: Sensor Selection

#### Standard Triplet

| Setting | Description |
|---------|-------------|
| **Flow sensor** | Volumetric flow rate (L/min, L/h, m³/h, or gal/min) |
| **Supply temperature** (Vorlauf) | Temperature of the outgoing water |
| **Return temperature** (Rücklauf) | Temperature of the returning water |
| **Pump entity** *(optional)* | Entity indicating pump state (binary_sensor, switch, etc.) |
| **Pump delay** *(optional)* | Seconds to wait after pump turns on before values are valid (default: 30) |
| **EMA smoothing factor (α)** *(optional)* | Smoothing factor for input sensors (default: 1.0 = off) |

#### Dual-Line (Special)

| Setting | Description |
|---------|-------------|
| **Supply temperature A / B** | Temperature sensors for each supply line |
| **Flow sensor A / B** | Flow rate sensors for each line |
| **Common return temperature** | Shared return temperature sensor |
| **Pump entity** *(optional)* | Entity indicating pump state |
| **Pump delay** *(optional)* | Seconds to wait after pump turns on (default: 30) |
| **EMA smoothing factor (α)** *(optional)* | Smoothing factor for input sensors (default: 1.0 = off) |

### Pump Gating

When a pump entity is configured, the integration suppresses invalid readings:

- **Pump turns on:** Waits for the configured delay (default 30s) before reporting real values. During the delay, power = 0.
- **Pump turns off:** Immediately sets power to 0 and stops energy accumulation.
- **Gated temperature sensors** are only available when the pump is active, preventing stale temperature readings from appearing in dashboards.

### EMA Smoothing

The optional Exponential Moving Average filter smooths noisy sensor inputs before power calculation:

```
smoothed = α × raw_value + (1 - α) × previous_smoothed
```

| α value | Effect |
|---------|--------|
| **1.0** | No smoothing (default) - raw values pass through |
| **0.3 - 0.5** | Light smoothing |
| **0.1 - 0.3** | Moderate smoothing |
| **< 0.1** | Heavy smoothing |

The EMA automatically resets when:
- A sensor becomes unavailable (fresh start on recovery)
- The pump state changes (no stale trailing values)

### Medium Selection

Pre-configured fluid properties are available for common heat transfer media:

| Medium | Specific Heat (kJ/(kg·K)) | Density (kg/L) |
|--------|---------------------------|-----------------|
| Water | 4.186 | 1.000 |
| Ethylene Glycol 20% | 3.860 | 1.025 |
| Ethylene Glycol 30% | 3.560 | 1.040 |
| Ethylene Glycol 40% | 3.260 | 1.054 |
| Propylene Glycol 20% | 3.920 | 1.017 |
| Propylene Glycol 30% | 3.680 | 1.026 |
| Propylene Glycol 40% | 3.430 | 1.034 |

Select **Custom** to enter your own specific heat capacity and density values.

## Energy Dashboard

The heating and cooling energy sensors use `SensorStateClass.TOTAL_INCREASING`, making them fully compatible with the Home Assistant Energy Dashboard.

1. Go to **Settings** → **Dashboards** → **Energy**
2. Add the heating/cooling energy sensors under **Gas consumption** or **Individual devices**

## Heating vs. Cooling

- **Positive ΔT** (supply > return) → Heating mode → Power is positive
- **Negative ΔT** (supply < return) → Cooling mode → Power is negative
- Heating energy accumulates only during heating (positive power)
- Cooling energy accumulates only during cooling (negative power, stored as positive value)
- The **System Energy** sensor provides the net balance: heating - cooling

### Circuit Mode

- **Source** (e.g. heat pump, boiler): System Power = Thermal Power (positive when producing heat)
- **Sink** (e.g. floor heating, radiator): System Power = -Thermal Power (positive when consuming heat)

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

### Funktionen

- Thermische Leistungsberechnung aus Durchfluss und Temperaturdifferenz
- Getrennte Heiz- & Kühlenergie-Zähler (kompatibel mit dem Energie-Dashboard)
- System-Energiesensor mit Nettobilanz
- Kreislaufmodus: Quelle (Wärmeerzeuger) oder Senke (Wärmeverbraucher)
- Medienauswahl: Wasser, Glykol-Gemische oder benutzerdefinierte Flüssigkeitseigenschaften
- Pumpen-Gating mit konfigurierbarer Verzögerung
- EMA-Glättung (Exponential Moving Average) für verrauschte Sensorwerte
- Automatische Einheitenumrechnung (L/min, L/h, m³/h, gal/min)
- Trapezintegration für präzise Energieberechnung
- Übersteht Neustarts dank Zustandswiederherstellung

### Konfigurationstypen

**Standard-Triplet:**
- Durchflusssensor (L/min, m³/h, etc.)
- Vorlauftemperatur
- Rücklauftemperatur

**Dual-Line (Spezial):**
- Vorlauftemperatur A + Durchflusssensor A
- Vorlauftemperatur B + Durchflusssensor B
- Gemeinsame Rücklauftemperatur

### Optionale Einstellungen

- **Pumpenentität** - Unterdrückt ungültige Messwerte wenn die Pumpe aus ist
- **Pumpenverzögerung** - Wartezeit nach dem Einschalten der Pumpe (Standard: 30 Sekunden)
- **EMA-Glättungsfaktor (α)** - 1.0 = aus, kleinere Werte = stärkere Glättung (empfohlen: 0.1–0.5)
- **Wärmeträgermedium** - Wasser, Glykol-Gemische, oder benutzerdefiniert

### Erstellte Sensoren

- **Thermische Leistung** (kW) - positiv = Heizen, negativ = Kühlen
- **Systemleistung** (kW) - vorzeichenbereinigt je nach Kreislaufmodus
- **Heizenergie** (kWh) - akkumuliert nur bei positiver Leistung
- **Kühlenergie** (kWh) - akkumuliert nur bei negativer Leistung
- **Systemenergie** (kWh) - Nettobilanz (Heizen - Kühlen)
- **Temperaturdifferenz ΔT** (°C) - Vorlauf minus Rücklauf
- **Durchflussrate** (L/min) - normalisierte Durchflussmenge
- **Kreislaufmodus** - Diagnose: zeigt aktuellen Modus (Quelle/Senke)

### Installation

1. HACS öffnen → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. `https://github.com/timzifer/ha-heating-power-flow` als **Integration** hinzufügen
3. "Heating Power Flow" suchen und installieren
4. Home Assistant neu starten

## License

MIT
