# MeshCore Utility Scripts

## Scripts

### `test_device.py`
Interactive device connection test and information display.

**Features:**
- Interactive serial port selection (lists available ports)
- Device information (model, firmware version, max contacts/channels)
- Self information (device name, public key, coordinates)
- Battery status (voltage and approximate percentage)
- Storage information (used/total in MB/KB)

**Usage:**
```bash
# Interactive mode - lists available ports
python scripts/test_device.py

# Direct port specification
python scripts/test_device.py /dev/tty.usbmodem90706983D6801
```

---

### `channel_bot.py`
Bot that sends messages to a channel at regular intervals (default: every 60 seconds).

**Usage:**
```bash
# Default: channel 0, default message, 60 second interval
python scripts/channel_bot.py

# Custom channel
python scripts/channel_bot.py 1

# Custom channel and message
python scripts/channel_bot.py 0 "My custom bot message"
```

**Configuration:** Edit `PORT`, `CHANNEL_IDX`, `MESSAGE`, or `INTERVAL_SECONDS` in the script.

---

### `check_time_sync.py`
Check if device clock is synchronized with system time, and optionally sync it.

**Usage:**
```bash
# Check clock sync status
python scripts/check_time_sync.py

# Check and sync if needed
python scripts/check_time_sync.py --sync
```

**Features:**
- Compares system time with device time
- Shows difference in seconds/minutes/hours
- Indicates if clocks are synced (within 5 seconds)
- Optionally syncs device time to system time

---

## Configuration

**Default port:** `/dev/tty.usbmodem90706983D6801` (edit `PORT` variable in each script to change)

**Note:** On macOS, use `tty` version (not `cu`) for serial ports. The `test_device.py` script automatically prefers `tty` over `cu` versions.
