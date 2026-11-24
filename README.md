# tenis4uMonitor

A background service that periodically checks court booking systems for free courts and posts the results to Discord.

Supported providers:

| Provider | Site | `facility_id` |
|---|---|---|
| `tenis4u` | [app.tenis4u.pl](https://app.tenis4u.pl) | numeric facility id, e.g. `"104"` |
| `twojtenis` | [app.twojtenis.pl](https://app.twojtenis.pl) | club GUID, e.g. `"958662f0-0bd2-4fdc-8bef-bb2d69761adb"` |

## How it works

Every `fetch_interval_minutes` (aligned to even boundaries, e.g. XX:00/20/40) the monitor, for each configured facility:

1. fetches free intervals for the facility's court type from its provider (tenis4u returns free hours directly; for twojtenis free time = opening hours minus public bookings),
2. clips them to the global `begin_time`–`end_time`, keeps only the selected `weekdays`, merges touching/overlapping intervals **per court** and drops windows shorter than `min_duration_minutes`,
3. compares them with the facility's previous snapshot (`snapshots/{key}.json`).

If anything changed, a Discord message lists the free windows per day, e.g. `16:30–19:00 · 3 courts`. `@everyone` is mentioned only for **new** windows — a window that grew, appeared, or a court that freed up. Shrinking windows don't ping. The very first run for a facility is a silent baseline.

## Requirements

- Python 3.11+
- Dependencies listed in [`requirements.txt`](./requirements.txt)

## Setup

```bash
git clone <repo-url>
cd tenis4uMonitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the webhook URLs
```

## Configuration

Non-secret settings live in [`config.toml`](./config.toml), optionally overridden by `config.{APP_ENV}.toml` (git-ignored). Secrets (webhook URLs) live in `.env` only.

```toml
fetch_interval_minutes = 20
max_proxies_ready = 5
days_ahead = 7                     # look-ahead horizon in days (1-14)

# Global filters, applied to every facility
begin_time = "16:30"
end_time = "22:30"
min_duration_minutes = 60
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

[discord]
mode = "global"                    # "global" | "per_facility" | "both"

[[facilities]]
key = "tenis4u_104"                # unique: lowercase letters, digits, single underscores
name = "tenis4u 104"               # shown in Discord
provider = "tenis4u"
facility_id = "104"
court_type = "badminton"           # tennis | badminton | padel
# booking_url = "https://..."      # optional override of the provider's booking link
```

The settings are validated at startup: unknown providers or court types, duplicate keys, `begin_time >= end_time` and missing webhooks for the chosen mode all fail fast with a clear message.

### Discord routing and environment variables

`APP_ENV` (`dev` or `prod`) selects the variable prefix.

| Mode | Sends | Required variables |
|---|---|---|
| `global` | one message with every facility to a shared channel | `{ENV}_DISCORD__GLOBAL_WEBHOOK_URL` |
| `per_facility` | a message per changed facility to its own channel | `{ENV}_DISCORD__FACILITY__{KEY}_WEBHOOK_URL` for every facility |
| `both` | both of the above | all of the above |

`{KEY}` is the facility `key` in upper case, e.g. `PROD_DISCORD__FACILITY__TENIS4U_104_WEBHOOK_URL`.

### Adding a facility

Add a `[[facilities]]` entry to `config.toml`. When using `per_facility`/`both`, also add its webhook variable to `.env` (and to the deploy secrets / [`deploy.yml`](./.github/workflows/deploy.yml)).

### Adding a provider

1. Create `src/providers/<name>.py` with a `SlotProvider` subclass: set `name`, `API_BASE_URL`, `WEB_BASE_URL`, `HEADERS`, and implement `fetch_availability()` (returning `CourtAvailability` intervals) and `booking_url()`. Keep response parsing in pure functions so it can be unit-tested without HTTP.
2. Register it in `PROVIDERS` in [`src/providers/__init__.py`](./src/providers/__init__.py).

## Running the monitor

```bash
python3 src/main.py
```

## Running tests

```bash
pytest
```

Tests run offline: HTTP, providers, the proxy service and Discord are replaced by fakes. Provider fixtures live in [`tests/fixtures/`](./tests/fixtures/).
