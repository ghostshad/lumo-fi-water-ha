# Lumo Water Consumption for Home Assistant

[![HACS Validate](https://github.com/lumo-water/ha-lumo-water/actions/workflows/validate.yaml/badge.svg)](https://github.com/lumo-water/ha-lumo-water/actions/workflows/validate.yaml)

Home Assistant custom integration that fetches daily water consumption data
(cold and warm water in liters) from the Lumo Finland customer portal.

## Features

- **10 sensor entities** — cumulative, daily, monthly, cost, and monthly cost
  readings for both cold and warm water
- **Cumulative sensors** — work with the Home Assistant Energy/Water dashboard
- **Cost tracking** — set your water prices per 1 000 L in the integration
  options, and get cost sensors in EUR
- **UI configuration** — add via `Settings > Devices & Services > Add Integration`
- **Automatic polling** — checks for new data every 6 hours
- **Full history** — all daily consumption data stored in sensor attributes

## Sensors

| Entity ID | State Class | Unit | Description |
|---|---|---|---|
| `sensor.lumo_water_cold_consumption` | `total_increasing` | L | All-time cumulative cold |
| `sensor.lumo_water_warm_consumption` | `total_increasing` | L | All-time cumulative warm |
| `sensor.lumo_water_cold_daily` | `measurement` | L | Latest available day's cold |
| `sensor.lumo_water_warm_daily` | `measurement` | L | Latest available day's warm |
| `sensor.lumo_water_cold_monthly` | `measurement` | L | Current calendar month cold |
| `sensor.lumo_water_warm_monthly` | `measurement` | L | Current calendar month warm |
| `sensor.lumo_water_cold_cost` | `total_increasing` | EUR | All-time cold water cost |
| `sensor.lumo_water_warm_cost` | `total_increasing` | EUR | All-time warm water cost |
| `sensor.lumo_water_cold_cost_monthly` | `measurement` | EUR | Current month cold cost |
| `sensor.lumo_water_warm_cost_monthly` | `measurement` | EUR | Current month warm cost |

## Installation

### Via HACS (recommended)

1. Go to `HACS > Integrations > Custom repositories`
2. Add this repository URL with category **Integration**
3. Click **Install**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/lumo_water/` directory to your HA
   `config/custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── lumo_water/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── strings.json
           ├── config_flow.py
           ├── coordinator.py
           └── sensor.py
   ```

2. Restart Home Assistant

### Configuration

No YAML configuration needed. After restart:

1. Go to `Settings > Devices & Services`
2. Click `Add Integration`
3. Search for **Lumo Water Consumption**
4. Enter your **Contract UUID** (the fixed UUID from your API URL)
5. Submit — connection is validated immediately

### Setting Water Prices

After adding the integration, set your water prices to enable cost sensors:

1. Go to `Settings > Devices & Services`
2. Find **Lumo Water Meter** and click **Configure**
3. Enter the price per **1 000 liters** for cold and warm water
   (e.g., enter `5.50` if 1 000 L costs 5.50 EUR)
4. Submit — cost sensors update automatically after the next data refresh

> Prices are stored in the integration options. You can change them anytime
> by clicking **Configure** again.

### Docker + Supervisor

If running HA via Docker with the Supervisor:

- **HACS route**: Follow HACS steps above. HACS places files in the correct
  location automatically.
- **Manual route**: Use the **Samba** addon or **VS Code** addon to copy files
  into `config/custom_components/lumo_water/`, then restart.

## Data source

The integration calls the Lumo customer API endpoint:
`https://customer.mylumoapp.lumo.fi/api/contract-water-consumption/{uuid}`

Your UUID is the path segment after `/api/contract-water-consumption/` in the
water consumption page URL.

> Note: The API data can be delayed by a few days. The integration polls every
> 6 hours and picks up whatever data is available.

## Updating the Integration

### Via HACS

1. In HACS, the update badge appears when a new release is available
2. Click **Update** on the Lumo Water Consumption integration
3. Restart Home Assistant

### Manual update

1. Replace the entire `custom_components/lumo_water/` directory with the new version
2. Restart Home Assistant

### Creating a new version (for developers)

1. Edit `custom_components/lumo_water/manifest.json` and bump the `version` field
   (e.g., `1.1.0` → `1.2.0`)
2. Commit and push to GitHub
3. Create a new GitHub Release with the tag matching the version (e.g., `v1.2.0`)
4. HACS will automatically detect the new release for all users

## Requirements

- Home Assistant 2023.8.0 or newer
- A Lumo Finland water contract with an installed meter

## License

MIT
