# Production Deployment Guide

This guide covers deploying MeshCore Python scripts to remote production machines.

## Prerequisites

- Remote machine with Python 3.10+ installed
- Access to serial port (USB device connected)
- SSH access to remote machine
- User with appropriate permissions (serial port access)

## Deployment Methods

### Method 1: Git Clone (Recommended for Development/Updates)

**Best for:** Regular updates, version control, multiple environments

```bash
# On remote machine
cd /opt
git clone <your-repo-url> meshcore_py
cd meshcore_py

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Update scripts
cd scripts/AlertBot
python bot.py
```

**Update workflow:**
```bash
# On remote machine
cd /opt/meshcore_py
git pull
source venv/bin/activate
pip install -e .  # Update if dependencies changed
```

### Method 2: rsync (Recommended for Production)

**Best for:** Controlled deployments, minimal dependencies

```bash
# From your local machine
rsync -avz --exclude 'venv' --exclude '.git' \
  --exclude '__pycache__' --exclude '*.pyc' \
  meshcore_py/ user@remote:/opt/meshcore_py/

# On remote machine
cd /opt/meshcore_py
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Method 3: Package and Deploy

**Best for:** Standalone deployments, minimal setup

```bash
# Create deployment package
tar -czf meshcore_deploy.tar.gz \
  --exclude='venv' --exclude='.git' \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='tests' --exclude='examples' \
  meshcore_py/

# Transfer to remote
scp meshcore_deploy.tar.gz user@remote:/tmp/

# On remote machine
cd /opt
tar -xzf /tmp/meshcore_deploy.tar.gz
cd meshcore_py
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Installation Steps

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install -y python3 python3-pip

# Ensure serial port access
sudo usermod -a -G dialout $USER  # Linux
# Log out and back in for group changes to take effect
```

### 2. Install Python Dependencies

```bash
cd /opt/meshcore_py
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 3. Verify Serial Port Access

```bash
# List available ports
ls -l /dev/ttyUSB* /dev/ttyACM* /dev/tty.usbmodem*

# Test access
python3 -c "import serial; print('Serial access OK')"
```

## Process Management

### Option 1: systemd Service (Recommended)

Create a systemd service file for automatic startup and management:

```bash
sudo nano /etc/systemd/system/meshcore-bot.service
```

**Service file content:**

```ini
[Unit]
Description=MeshCore Alert Bot
After=network.target

[Service]
Type=simple
User=your-username
Group=dialout
WorkingDirectory=/opt/meshcore_py/scripts/AlertBot
Environment="PATH=/opt/meshcore_py/venv/bin"
ExecStart=/opt/meshcore_py/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable meshcore-bot

# Start service
sudo systemctl start meshcore-bot

# Check status
sudo systemctl status meshcore-bot

# View logs
sudo journalctl -u meshcore-bot -f
```

### Option 2: Supervisor

Install supervisor:

```bash
sudo apt-get install supervisor  # Ubuntu/Debian
```

Create supervisor config:

```bash
sudo nano /etc/supervisor/conf.d/meshcore-bot.conf
```

**Supervisor config:**

```ini
[program:meshcore-bot]
command=/opt/meshcore_py/venv/bin/python /opt/meshcore_py/scripts/AlertBot/bot.py
directory=/opt/meshcore_py/scripts/AlertBot
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/meshcore-bot.err.log
stdout_logfile=/var/log/meshcore-bot.out.log
environment=PATH="/opt/meshcore_py/venv/bin"
```

**Start supervisor:**

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start meshcore-bot
sudo supervisorctl status
```

### Option 3: screen/tmux (Simple, Not Recommended for Production)

```bash
# Using screen
screen -S meshcore-bot
cd /opt/meshcore_py/scripts/AlertBot
source ../../venv/bin/activate
python bot.py
# Press Ctrl+A then D to detach

# Reattach later
screen -r meshcore-bot
```

## Configuration

### Serial Port Configuration

The bot automatically saves the selected port to `.config.json`. On first run:

1. Connect the device
2. Run the bot interactively to select the port
3. The port will be saved for future runs

Or manually create `/opt/meshcore_py/scripts/AlertBot/.config.json`:

```json
{
  "port": "/dev/ttyUSB0"
}
```

### Environment Variables (Optional)

You can use environment variables for configuration:

```bash
# In systemd service file, add:
Environment="MESHCORE_PORT=/dev/ttyUSB0"
Environment="MESHCORE_CHANNEL=0"
```

Then modify `bot.py` to read from environment:

```python
import os
PORT = os.getenv('MESHCORE_PORT', None)
CHANNEL_IDX = int(os.getenv('MESHCORE_CHANNEL', '0'))
```

## Logging

### systemd Journal

```bash
# View recent logs
sudo journalctl -u meshcore-bot -n 50

# Follow logs
sudo journalctl -u meshcore-bot -f

# View logs since boot
sudo journalctl -u meshcore-bot -b

# Export logs
sudo journalctl -u meshcore-bot > bot.log
```

### Custom Logging

Modify `bot.py` to add file logging:

```python
import logging
from pathlib import Path

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

## Monitoring

### Health Check Script

Create a simple health check:

```bash
#!/bin/bash
# /opt/meshcore_py/scripts/health_check.sh

if systemctl is-active --quiet meshcore-bot; then
    echo "Bot is running"
    exit 0
else
    echo "Bot is not running!"
    exit 1
fi
```

### Monitoring with cron

```bash
# Check every 5 minutes
*/5 * * * * /opt/meshcore_py/scripts/health_check.sh || systemctl restart meshcore-bot
```

## Troubleshooting

### Permission Issues

```bash
# Check serial port permissions
ls -l /dev/ttyUSB*

# Add user to dialout group
sudo usermod -a -G dialout $USER

# Check current groups
groups
```

### Port Not Found

```bash
# List all serial ports
ls -l /dev/tty* | grep -E 'USB|ACM|usbmodem'

# Check if device is connected
dmesg | tail -20

# Test port manually
python3 -c "import serial.tools.list_ports; [print(p.device) for p in serial.tools.list_ports.comports()]"
```

### Python Path Issues

```bash
# Verify virtual environment
which python
# Should show: /opt/meshcore_py/venv/bin/python

# Verify meshcore is installed
python -c "import meshcore; print(meshcore.__file__)"
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status meshcore-bot

# Check logs
sudo journalctl -u meshcore-bot -n 100

# Test manually
cd /opt/meshcore_py/scripts/AlertBot
source ../../venv/bin/activate
python bot.py
```

## Security Considerations

1. **User Permissions**: Run service as non-root user
2. **File Permissions**: Restrict access to config files
   ```bash
   chmod 600 /opt/meshcore_py/scripts/AlertBot/.config.json
   ```
3. **Network Security**: If using TCP connections, use firewall rules
4. **Log Rotation**: Configure log rotation to prevent disk fill

## Backup and Recovery

### Backup Configuration

```bash
# Backup config
cp /opt/meshcore_py/scripts/AlertBot/.config.json /backup/meshcore-config-$(date +%Y%m%d).json
```

### Recovery Procedure

```bash
# Restore from backup
cd /opt/meshcore_py
git pull  # or restore from backup
source venv/bin/activate
pip install -e .
sudo systemctl restart meshcore-bot
```

## Quick Deployment Script

Create a deployment script for easy updates:

```bash
#!/bin/bash
# deploy.sh

REMOTE_USER="your-username"
REMOTE_HOST="your-server"
REMOTE_PATH="/opt/meshcore_py"

echo "Deploying to $REMOTE_USER@$REMOTE_HOST..."

# Sync files
rsync -avz --exclude 'venv' --exclude '.git' \
  --exclude '__pycache__' --exclude '*.pyc' \
  --exclude 'tests' --exclude 'examples' \
  ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

# Run remote commands
ssh $REMOTE_USER@$REMOTE_HOST << 'EOF'
cd /opt/meshcore_py
source venv/bin/activate
pip install -e .
sudo systemctl restart meshcore-bot
sudo systemctl status meshcore-bot
EOF

echo "Deployment complete!"
```

Make it executable:

```bash
chmod +x deploy.sh
./deploy.sh
```

## Docker Deployment

### Automatic Build with GitHub Actions

The Docker image is automatically built when you push to the `dev-axistem` branch. The workflow is configured in `.github/workflows/docker-build.yml`.

**Features:**
- Automatic build on push to `dev-axistem` branch
- Image tagged as `dev-axistem`
- Multi-platform support (amd64, arm64)
- Build cache for faster builds

**To enable pushing to a registry:**
1. Uncomment the Docker login step in `.github/workflows/docker-build.yml`
2. Add secrets to GitHub:
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`
3. Set `push: true` in the build step

### Manual Docker Build

Build the image locally:

```bash
# From project root
docker build -t meshcore-bot:dev-axistem -f Dockerfile .
```

### Running the Container

#### Option 1: Using docker-compose (Recommended)

```bash
# Edit docker-compose.yml to set your device path
nano docker-compose.yml

# Start container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

#### Option 2: Using docker run

```bash
# Map your host device to /dev/ttyUSB0 inside container
# Replace HOST_DEVICE with your actual device path
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device HOST_DEVICE:/dev/ttyUSB0 \
  meshcore-bot:dev-axistem

# With directory mount (for logs and config)
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device HOST_DEVICE:/dev/ttyUSB0 \
  -v $(pwd)/scripts/AlertBot:/app/scripts/AlertBot \
  meshcore-bot:dev-axistem
```


### Device Configuration

**Important:** Inside the container, the device is always `/dev/ttyUSB0`. Map your host device to it:

- **Format:** `HOST_DEVICE:/dev/ttyUSB0`
- The bot uses `/dev/ttyUSB0` by default (no arguments needed)

**Directory mount (recommended):** Mount the AlertBot directory for logs and config persistence:
```bash
-v $(pwd)/scripts/AlertBot:/app/scripts/AlertBot
```

### Dockerfile Details

The Dockerfile:
- Uses Python 3.10 slim base image
- Installs system dependencies for serial communication
- Copies project files and installs dependencies
- Sets working directory to `scripts/AlertBot`
- Runs `bot.py` by default

### Notes

- **Device mapping**: Use `--device` flag to pass through serial devices
- **Config file**: Optional - the bot accepts port as command-line argument
- **Logs**: Use `docker logs -f meshcore-bot` to view output
- **Restart policy**: Use `--restart unless-stopped` for automatic restart

## Summary

**Recommended Production Setup:**

1. Deploy using **rsync** or **git clone**
2. Use **systemd service** for process management
3. Run as **non-root user** with dialout group
4. Enable **automatic restart** on failure
5. Monitor with **journalctl** or custom logging
6. Set up **health checks** and monitoring

This provides a robust, maintainable production deployment.

