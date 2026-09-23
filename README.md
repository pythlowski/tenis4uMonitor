# tenis4uMonitor

A background monitoring service that periodically polls the [tenis4u.pl](https://tenis4u.pl) API for free court slots and sends a Discord notification whenever availability changes.

## How it works

The monitor fetches available court slots at a configured interval (default: every 20 minutes). It compares each new snapshot to the previous one — if anything has changed, it fires a Discord webhook alert with a summary of newly available slots.

## Requirements

- Python 3.10+
- Dependencies listed in [`requirements.txt`](./requirements.txt)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd tenis4uMonitor
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your Discord webhook URL(s):

```bash
cp .env.example .env
```

Then open `.env` and replace the placeholder values with your actual webhook URLs.

> The active environment is controlled by `APP_ENV`. Set it to `dev` or `prod` to pick the corresponding webhook URL.

### 5. (Optional) Adjust monitoring settings

Edit [`config.toml`](./config.toml) to change the monitored facility, court type, time window, weekdays, or fetch interval.

## Running the monitor

```bash
python3 src/main.py
```

The service runs in an infinite loop, polling the API and sending Discord alerts on changes.

## Running tests

```bash
pytest
```

Tests are located in the [`tests/`](./tests/) directory and cover slot computation, snapshot comparison, and free slot diffing logic.

