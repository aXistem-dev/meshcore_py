# MeshCore Utility Scripts

## Scripts

### `AlertBot/bot.py`
Alert bot that sends messages to a channel at configurable intervals.

**Local Usage:**
```bash
python scripts/AlertBot/bot.py [port] [channel_index]
```

`port` and `channel_index` are optional. The command can run without those arguments, where you will be asked which serial device you want to use. The default channel will be Channel `0` = Public channel

**Setting Environment Variables (Local Python):**

To configure the bot with environment variables when running locally, set them before running:

**Linux/macOS:**
```bash
# Export variables in your shell
export MESHCORE_CHANNEL_IDX=0
export MESHCORE_MESSAGE_INTERVAL=300 # In seconds
export MESHCORE_CYCLE_INTERVAL=180 # In minutes
export MESHCORE_MESSAGES='["Message 1","Message 2"]'

# Or inline with the command
MESHCORE_MESSAGE_INTERVAL=300 MESHCORE_CYCLE_INTERVAL=180 python scripts/AlertBot/bot.py
```

**Windows (PowerShell):**
```powershell
$env:MESHCORE_CHANNEL_IDX=0
$env:MESHCORE_MESSAGE_INTERVAL=300 # In seconds
$env:MESHCORE_CYCLE_INTERVAL=180 # In minutes
$env:MESHCORE_MESSAGES='["Message 1","Message 2"]'
python scripts/AlertBot/bot.py
```

**Windows (CMD):**
```cmd
set MESHCORE_CHANNEL_IDX=0
set MESHCORE_MESSAGE_INTERVAL=300 # In seconds
set MESHCORE_CYCLE_INTERVAL=180 # In Minutes
set MESHCORE_MESSAGES=["Message 1","Message 2"]
python scripts/AlertBot/bot.py
```

**Tip:** Create a shell script to load variables:
```bash
#!/bin/bash
export MESHCORE_CHANNEL_IDX=0
export MESHCORE_MESSAGE_INTERVAL=300 # In seconds
export MESHCORE_CYCLE_INTERVAL=180 # In minutes
export MESHCORE_MESSAGES='["Message 1","Message 2"]'
python scripts/AlertBot/bot.py
```

**Docker Deployment:**
```bash
# 1. Configure environment
cp scripts/AlertBot/meshcore-alertbot.env /path/to/deployment/
# Edit meshcore-alertbot.env with your settings

# 2. Deploy with Docker Compose
docker compose -f stack-meshcore-alertbot.yaml up -d

# 3. View logs
docker logs -f meshcore-alertbot
```

**Configuration (via environment variables):**
- `MESHCORE_CHANNEL_IDX` - Channel index (default: 0)
- `MESHCORE_MESSAGE_INTERVAL` - Seconds between messages (default: 300)
- `MESHCORE_CYCLE_INTERVAL` - Minutes between cycles (default: 180)
- `MESHCORE_MESSAGES` - JSON array or newline-separated messages

**Files:**
- `stack-meshcore-alertbot.yaml` - Docker Compose stack file
- `meshcore-alertbot.env` - Environment configuration template
- `logs/bot.log` - Log file (mounted volume in Docker)

---

### `Configuration/device_info.py`
Interactive device connection test and information display.

**Usage:**
```bash
# Interactive mode - lists available ports
python scripts/Configuration/device_info.py

# Direct port specification
python scripts/Configuration/device_info.py /dev/ttyUSB0
```

**Features:** Device info, firmware, battery, storage, coordinates

---

### `Configuration/time_sync.py`
Check and sync device clock with system time.

**Usage:**
```bash
# Check sync status
python scripts/Configuration/time_sync.py

# Sync if needed
python scripts/Configuration/time_sync.py --sync
```

---

## Docker Deployment

### AlertBot Quick Start

1. **Prepare deployment directory:**
   ```bash
   mkdir -p /opt/meshcore-alertbot
   cd /opt/meshcore-alertbot
   ```

2. **Copy configuration files:**
   ```bash
   cp /path/to/meshcore_py/scripts/AlertBot/stack-meshcore-alertbot.yaml .
   cp /path/to/meshcore_py/scripts/AlertBot/meshcore-alertbot.env .
   mkdir -p meshcore-alertbot-data/logs
   ```

3. **Edit environment file:**
   ```bash
   nano meshcore-alertbot.env
   # Set MESHCORE_DEVICE to your device path (e.g., /dev/ttyACM0)
   # Configure messages, intervals, etc.
   ```

4. **Deploy:**
   ```bash
   docker compose -f stack-meshcore-alertbot.yaml pull
   docker compose -f stack-meshcore-alertbot.yaml up -d
   ```

5. **Monitor:**
   ```bash
   docker logs -f meshcore-alertbot
   # Or view log file
   tail -f meshcore-alertbot-data/logs/bot.log
   ```

**Image:** `ghcr.io/axistem-dev/meshcore-alertbot:dev-axistem`

**Volume Mounts:**
- `./meshcore-alertbot-data/logs` → `/app/scripts/AlertBot/logs` (logs only)
- Device: `${MESHCORE_DEVICE}` → `/dev/ttyUSB0` (inside container)

---

## Notes

- Scripts use interactive port selection if no port is specified
- Docker deployment requires device passthrough (Linux recommended)
- Logs are stored in `logs/` subdirectory for cleaner volume management
- All bot settings configurable via environment variables (no rebuild needed)
