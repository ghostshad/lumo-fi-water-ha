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
- **Configurable polling** — checks for new data every 6 hours by default,
  adjustable in integration options (min 1 hour)
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

### Integration Options

After adding the integration, click **Configure** on **Lumo Water Meter** to
adjust these settings:

- **API URL** — the endpoint URL for fetching water data. Defaults to
  `https://customer.mylumoapp.lumo.fi/api/contract-water-consumption/{uuid}`.
  Update this if Lumo changes their API.
- **Poll interval (seconds)** — how often to fetch data. Default is `21600`
  (6 hours). Minimum `3600` (1 hour).
- **Cold / Warm water price (EUR / 1 000 L)** — set to enable cost sensors.
  Enter `5.50` if 1 000 L costs 5.50 EUR. Set to `0` to disable.

Settings take effect after the next data refresh or on restart.

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

> Note: The API data can be delayed by a few days. The integration polls at the
> configured interval (default 6 hours) and picks up whatever data is available.
> To change the polling frequency, go to **Configure** on the integration and
> adjust **Poll interval**.

## Dashboards & Cards

### Statistics graph (built-in, no additional cards needed)

Add a bar chart of daily consumption for the last 30 days:

1. Edit your dashboard → **Add Card** → **Statistics Graph**
2. Set **Entities** to `sensor.lumo_water_cold_daily` and `sensor.lumo_water_warm_daily`
3. Set **Period** to `Day`, **Days to show** to `30`, **Chart type** to `Bar`

Or paste this YAML in **Manual** card mode:

```yaml
type: statistics-graph
chart_type: bar
period: day
days_to_show: 30
stat_types:
  - mean
entities:
  - sensor.lumo_water_cold_daily
  - sensor.lumo_water_warm_daily
```

### ApexCharts Card (more customization)

Install **ApexCharts Card** from HACS, then add:

```yaml
type: custom:apexcharts-card
graph_span: 30d
span:
  offset: '-30d'
series:
  - entity: sensor.lumo_water_cold_daily
    type: column
    name: Cold
    stroke_width: 0
  - entity: sensor.lumo_water_warm_daily
    type: column
    name: Warm
    stroke_width: 0
```

### Energy dashboard (cumulative usage)

Add the cumulative sensors to the built-in Energy dashboard:

1. Go to `Settings > Energy`
2. Under **Water**, click **Add Water Source**
3. Select `sensor.lumo_water_cold_consumption` and/or `sensor.lumo_water_warm_consumption`

## Automations

### High daily usage alert

Send a notification when daily cold water exceeds 500 L:

```yaml
alias: Water usage alert
triggers:
  - trigger: state
    entity_id: sensor.lumo_water_cold_daily
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: High water usage
      message: >
        Cold water consumption today: {{ states('sensor.lumo_water_cold_daily') }} L
    enabled: "{{ states('sensor.lumo_water_cold_daily') | int(0) > 500 }}"
```

### Monthly cost threshold

Warn when monthly cost exceeds a budget:

```yaml
alias: Monthly water budget alert
triggers:
  - trigger: state
    entity_id: sensor.lumo_water_cold_cost_monthly
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Water budget warning
      message: >
        Cold water cost this month:
        {{ states('sensor.lumo_water_cold_cost_monthly') }} EUR
    enabled: "{{ states('sensor.lumo_water_cold_cost_monthly') | float(0) > 30 }}"
```

### Daily consumption log (persistent notification)

```yaml
alias: Log daily water
triggers:
  - trigger: time
    at: "22:00:00"
conditions:
  - condition: template
    value_template: "{{ states('sensor.lumo_water_cold_daily') != 'unavailable' }}"
actions:
  - action: persistent_notification.create
    data:
      title: Daily water summary
      message: >
        Cold: {{ states('sensor.lumo_water_cold_daily') }} L |
        Warm: {{ states('sensor.lumo_water_warm_daily') }} L |
        Total: {{ states('sensor.lumo_water_cold_daily') | int(0) + states('sensor.lumo_water_warm_daily') | int(0) }} L
```

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
