# Docker Deployment Guide

## Quick Start

### Build Image

```bash
docker build -t meshcore-alertbot:dev-axistem .
```

### Run Container

The container always uses `/dev/ttyUSB0` internally. Map your host device to it:

```bash
# Linux example
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  meshcore-alertbot:dev-axistem

# macOS example (if device passthrough works)
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device /dev/cu.usbmodem90706983D6801:/dev/ttyUSB0 \
  meshcore-alertbot:dev-axistem
```

**Note:** Inside the container, the device is always `/dev/ttyUSB0`. The host device path can be anything.

## Automatic Builds

The Docker image is automatically built when you push to the `dev-axistem` branch via GitHub Actions.

### Workflow Configuration

The workflow (`.github/workflows/docker-build.yml`) will:
- Trigger on push to `dev-axistem` branch
- Build the Docker image
- Tag it as `dev-axistem`
- Push to GitHub Container Registry (ghcr.io)

### Image Location

Images are automatically pushed to:
```
ghcr.io/axistem-dev/meshcore-alertbot:dev-axistem
```

### Pulling the Image

```bash
docker pull ghcr.io/axistem-dev/meshcore-alertbot:dev-axistem
```

**Note:** For private repositories, you may need to authenticate:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## Device Mapping

**Important:** Inside the container, the device is always `/dev/ttyUSB0`. Map your host device to it:

- **Format:** `HOST_DEVICE:/dev/ttyUSB0`
- **Linux example:** `/dev/ttyUSB0:/dev/ttyUSB0`
- **macOS example:** `/dev/cu.usbmodem90706983D6801:/dev/ttyUSB0`

The bot is configured to use `/dev/ttyUSB0` by default.

## Usage Examples

### Basic Run

```bash
# Replace HOST_DEVICE with your actual device path
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device HOST_DEVICE:/dev/ttyUSB0 \
  meshcore-alertbot:dev-axistem
```

### With Directory Mount (for logs and config)

```bash
docker run -d \
  --name meshcore-bot \
  --restart unless-stopped \
  --device HOST_DEVICE:/dev/ttyUSB0 \
  -v $(pwd)/scripts/AlertBot:/app/scripts/AlertBot \
  meshcore-alertbot:dev-axistem
```

### Using docker-compose

1. Edit `docker-compose.yml` and set your host device path
2. Start: `docker-compose up -d`
3. Logs: `docker-compose logs -f`

## Finding Your Device

```bash
# Linux
ls -l /dev/ttyUSB* /dev/ttyACM*

# macOS
ls -l /dev/cu.* /dev/tty.* | grep -i usb

# Or use Python
python3 -c "from serial.tools import list_ports; [print(p.device) for p in list_ports.comports()]"
```

## macOS Note

Docker Desktop on macOS has limited USB device passthrough support. For production, deploy to a Linux server where device passthrough works reliably.

## Troubleshooting

### Check Logs

```bash
docker logs meshcore-bot
docker logs -f meshcore-bot  # Follow logs
```

### Run Interactively

```bash
docker run -it --rm \
  --device HOST_DEVICE:/dev/ttyUSB0 \
  meshcore-alertbot:dev-axistem
```

### Permission Issues

```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER
```

