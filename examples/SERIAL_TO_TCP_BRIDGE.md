# MeshCore Serial-to-TCP Bridge

This script bridges a MeshCore device connected via serial (USB) to TCP, allowing remote clients to connect to the device over the network.

## Quick Start

### On Raspberry Pi

1. **Install dependencies:**
   ```bash
   pip install meshcore
   # or if you have the source:
   pip install -e /path/to/meshcore_py
   ```

2. **Run the bridge:**
   ```bash
   python3 serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000
   ```

3. **Connect from another machine:**
   ```bash
   # Using meshcore-cli
   meshcli -t raspberry-pi-ip -p 5000 infos
   
   # Using Python
   from meshcore import MeshCore
   meshcore = await MeshCore.create_tcp("raspberry-pi-ip", 5000)
   ```

## Usage

```bash
python3 serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000 --baud 115200
```

### Arguments

- `-s, --serial`: Serial port path (required, e.g., `/dev/ttyUSB0`)
- `-p, --port`: TCP port to listen on (default: 5000)
- `-b, --baud`: Serial baudrate (default: 115200)
- `--host`: TCP host to bind to (default: 0.0.0.0 for all interfaces)
- `-v, --verbose`: Enable verbose logging

## Running as a Service

1. **Copy the service file:**
   ```bash
   sudo cp meshcore-serial-tcp-bridge.service /etc/systemd/system/
   ```

2. **Edit the service file:**
   ```bash
   sudo nano /etc/systemd/system/meshcore-serial-tcp-bridge.service
   ```
   
   Update the paths:
   - `ExecStart`: Path to the Python script
   - `--serial`: Your serial port (e.g., `/dev/ttyUSB0`)
   - `User`: Your username (default: `pi`)

3. **Enable and start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable meshcore-serial-tcp-bridge.service
   sudo systemctl start meshcore-serial-tcp-bridge.service
   ```

4. **Check status:**
   ```bash
   sudo systemctl status meshcore-serial-tcp-bridge.service
   ```

5. **View logs:**
   ```bash
   sudo journalctl -u meshcore-serial-tcp-bridge.service -f
   ```

## Alternative Solutions

### Using `socat` (Simple but less robust)

If you want a simpler solution without frame parsing, you can use `socat`:

```bash
# Install socat
sudo apt-get install socat

# Run bridge (raw serial to TCP, no frame parsing)
socat TCP-LISTEN:5000,fork,reuseaddr /dev/ttyUSB0,raw,nonblock,waitlock=/var/run/ttyUSB0.lock
```

**Note:** `socat` forwards raw bytes without understanding MeshCore's frame protocol. The Python bridge is recommended as it properly handles frame boundaries.

### Using `ser2net` (More features)

For a more feature-rich solution:

```bash
# Install ser2net
sudo apt-get install ser2net

# Configure in /etc/ser2net.yaml
connection: &meshcore
    accepter: tcp,5000
    connector: serialdev,/dev/ttyUSB0,115200n81,local
```

## Troubleshooting

### Serial port not found

- Check if the device is connected: `ls -l /dev/ttyUSB*`
- Check permissions: `sudo usermod -a -G dialout $USER` (logout/login required)
- Check if another process is using the port: `lsof /dev/ttyUSB0`

### TCP connection refused

- Check if the bridge is running: `netstat -tlnp | grep 5000`
- Check firewall: `sudo ufw allow 5000/tcp`
- Check if binding to correct interface (use `--host 0.0.0.0` for all interfaces)

### Frame parsing errors

- Enable verbose logging: `-v` flag
- Check baudrate matches device: `--baud 115200` (or device's baudrate)
- Ensure only one client connects at a time (current implementation)

## How It Works

The bridge:
1. Connects to the MeshCore device via serial port
2. Listens for TCP connections on the specified port
3. Forwards MeshCore frames (with proper frame parsing) between serial and TCP clients
4. Supports multiple TCP clients (broadcasts serial data to all clients)
5. Handles frame boundaries correctly (0x3C + 2-byte size + payload)

The frame format is: `\x3c` + 2 bytes (little-endian size) + payload

