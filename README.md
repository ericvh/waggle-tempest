# Tempest Weather Station Waggle Plugin

A standalone Waggle plugin that receives UDP broadcasts from a local Tempest weather station and publishes the data to the Waggle message stream.

## Overview

This plugin extracts the Tempest functionality from the main waggle-davis project and provides it as an independent service. It listens for UDP broadcasts from Tempest weather stations and publishes comprehensive weather data including wind, temperature, humidity, pressure, precipitation, and lightning information.

## Features

- **Real-time Data Publishing**: Publishes Tempest weather data to Waggle message stream
- **Comprehensive Weather Data**: Wind speed/direction, temperature, humidity, pressure, precipitation, lightning
- **Multiple Data Sources**: Supports both observation (`obs_st`) and rapid wind (`rapid_wind`) messages
- **Automatic Parsing**: Parses Tempest UDP message formats automatically
- **Robust Error Handling**: Continues operating even with intermittent data issues
- **Docker Support**: Containerized for easy deployment
- **Configurable**: Customizable UDP port, publish intervals, and debug modes

## Published Data Topics

All data is published with:
- **Scope**: `beehive` (data sent to central server for analysis)
- **Sensor**: `tempest-weather-station` (identifies the data source)
- **Missing Value**: `-9999.0` (numeric) or `"unknown"` (string) for invalid/missing data
- **Timestamps**: Explicit UTC timestamps for all measurements

Example metadata structure:
```python
{
  "sensor": "tempest-weather-station",
  "units": "knots",
  "description": "Tempest average wind speed",
  "source": "obs_st",
  "missing": -9999.0
}
```

### Wind Data
- `tempest.wind.speed.lull` - Wind lull speed (knots)
- `tempest.wind.speed.avg` - Average wind speed (knots)
- `tempest.wind.speed.gust` - Wind gust speed (knots)
- `tempest.wind.direction` - Wind direction (degrees)
- `tempest.wind.speed.instant` - Instant wind speed (knots, rapid updates)
- `tempest.wind.direction.instant` - Instant wind direction (degrees, rapid updates)

### Environmental Data
- `tempest.pressure` - Barometric pressure (hPa)
- `tempest.temperature` - Air temperature (°C)
- `tempest.humidity` - Relative humidity (%)

### Light Data
- `tempest.light.illuminance` - Illuminance (lux)
- `tempest.light.uv_index` - UV index
- `tempest.light.solar_radiation` - Solar radiation (W/m²)

### Precipitation Data
- `tempest.rain.since_report` - Rain since last report (mm)
- `tempest.rain.daily` - Daily rainfall (mm)

### Lightning Data
- `tempest.lightning.distance` - Lightning distance (km)
- `tempest.lightning.count` - Lightning strike count

### System Data
- `tempest.battery` - Battery voltage (V)
- `tempest.report_interval` - Report interval (minutes)
- `tempest.hub.firmware` - Hub firmware version
- `tempest.hub.uptime` - Hub uptime (seconds)
- `tempest.hub.rssi` - Signal strength (dBm)
- `tempest.status` - Plugin status (1=active, 0=error)

## Installation

### Docker (Recommended)

#### Using Pre-built Multi-Arch Images

The plugin is automatically built and published as multi-architecture Docker images (amd64, arm64) on GitHub Container Registry:

```bash
# Pull and run the latest image
docker run --network host ghcr.io/[YOUR_USERNAME]/waggle-tempest:latest

# Run with custom environment variables
docker run --network host \
  -e TEMPEST_DEBUG=true \
  -e TEMPEST_PUBLISH_INTERVAL=30 \
  ghcr.io/[YOUR_USERNAME]/waggle-tempest:latest
```

#### Building from Source

```bash
# Clone and build the container
git clone <repository-url>
cd waggle-tempest
docker build -t tempest-weather-plugin .

# Run with host networking (required for UDP broadcasts)
docker run --network host tempest-weather-plugin
```

### Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the plugin
python3 main.py
```

## Usage

### Basic Usage

```bash
# Run with default settings
python3 main.py

# Run with debug output
python3 main.py --debug

# Use custom UDP port
python3 main.py --udp-port 50223

# Set custom publish interval
python3 main.py --publish-interval 30
```

### Docker Usage

#### Using GitHub Container Registry (Multi-Arch)

```bash
# Basic deployment using pre-built multi-arch image
docker run --network host ghcr.io/[YOUR_USERNAME]/waggle-tempest:latest

# With environment variables
docker run --network host \
  -e TEMPEST_UDP_PORT=50222 \
  -e TEMPEST_PUBLISH_INTERVAL=30 \
  -e TEMPEST_DEBUG=true \
  ghcr.io/[YOUR_USERNAME]/waggle-tempest:latest

# With command-line arguments (overrides environment variables)
docker run --network host ghcr.io/[YOUR_USERNAME]/waggle-tempest:latest \
  --debug \
  --udp-port 50223 \
  --publish-interval 45
```

#### Local Build Usage

```bash
# Build locally first
docker build -t tempest-weather-plugin .

# Basic deployment (uses defaults)
docker run --network host tempest-weather-plugin

# With environment variables (recommended for Docker)
docker run --network host \
  -e TEMPEST_UDP_PORT=50222 \
  -e TEMPEST_PUBLISH_INTERVAL=30 \
  -e TEMPEST_DEBUG=true \
  -e TEMPEST_NO_FIREWALL=false \
  tempest-weather-plugin
```

## Configuration

All configuration options can be set via either **environment variables** or **command-line arguments**. Command-line arguments take precedence over environment variables.

### Environment Variables

| Variable | Description | Type | Default |
|----------|-------------|------|---------|
| `TEMPEST_UDP_PORT` | UDP port to listen for broadcasts | integer | `50222` |
| `TEMPEST_PUBLISH_INTERVAL` | Minimum publish interval in seconds | integer | `60` |
| `TEMPEST_DEBUG` | Enable debug output | boolean | `false` |
| `TEMPEST_NO_FIREWALL` | Skip firewall setup warnings | boolean | `false` |

**Boolean values**: Use `true`, `1`, `yes`, or `on` for true; anything else is false.

**Example**:
```bash
export TEMPEST_UDP_PORT=50222
export TEMPEST_PUBLISH_INTERVAL=30
export TEMPEST_DEBUG=true
export TEMPEST_NO_FIREWALL=false
python3 main.py
```

### Command Line Arguments

| Argument | Description | Type | Default | Env Variable |
|----------|-------------|------|---------|--------------|
| `--udp-port PORT` | UDP port for Tempest broadcasts | integer | `50222` | `TEMPEST_UDP_PORT` |
| `--publish-interval SECONDS` | Minimum publish interval | integer | `60` | `TEMPEST_PUBLISH_INTERVAL` |
| `--debug` | Enable debug output | flag | `false` | `TEMPEST_DEBUG` |
| `--no-firewall` | Skip firewall setup warnings | flag | `false` | `TEMPEST_NO_FIREWALL` |

**Example**:
```bash
python3 main.py --debug --udp-port 50223 --publish-interval 30
```

### Configuration Priority

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Built-in defaults** (lowest priority)

The plugin will display which environment variables are being used at startup:
```
📌 Using environment variables: UDP_PORT, PUBLISH_INTERVAL
```

## Network Requirements

### UDP Port Access

The plugin requires access to UDP port 50222 (default) to receive Tempest broadcasts. This typically requires:

1. **Same Network**: Tempest station and plugin must be on the same network
2. **Firewall Configuration**: UDP port 50222 must be accessible
3. **Broadcasting Enabled**: Tempest station must have UDP broadcasting enabled

### Firewall Setup

If you encounter connectivity issues, you may need to configure firewall rules:

```bash
# Allow UDP port 50222
sudo iptables -I INPUT -p udp --dport 50222 -j ACCEPT

# Or use the firewall-opener container from the main project
docker run --privileged firewall-opener
```

## Integration with Main Project

This plugin can be used alongside the main waggle-davis project:

### Sidecar Deployment

```bash
# Start firewall opener
docker run --privileged --name firewall-opener -d firewall-opener

# Start Tempest plugin
docker run --network container:firewall-opener --name tempest-plugin -d tempest-weather-plugin

# Start Davis plugin (with --no-firewall since firewall is handled separately)
docker run --device=/dev/ttyACM2 --name davis-plugin -d waggle-davis --no-firewall
```

### Docker Compose

```yaml
version: '3.8'
services:
  firewall-opener:
    build: ../firewall-opener
    privileged: true
    restart: unless-stopped
    
  tempest-plugin:
    build: .
    network_mode: host
    depends_on:
      - firewall-opener
    restart: unless-stopped
    
  davis-plugin:
    build: ..
    devices:
      - /dev/ttyACM2:/dev/ttyACM2
    command: ["--no-firewall"]
    restart: unless-stopped
```

## Troubleshooting

### No Data Received

1. **Check Network**: Ensure Tempest station and plugin are on same network
2. **Verify Broadcasting**: Confirm Tempest station has UDP broadcasting enabled
3. **Firewall Issues**: Check if UDP port 50222 is accessible
4. **Port Conflicts**: Try different UDP port with `--udp-port`

### Debug Mode

Enable debug output to see detailed information:

```bash
python3 main.py --debug
```

This will show:
- UDP listener status
- Received message types
- Parsing errors
- Publication confirmations

### Testing Connection

Test UDP connectivity:

```bash
# Test port accessibility
netstat -uln | grep 50222

# Test with netcat (if Tempest is broadcasting)
nc -u -l 50222
```

## Data Flow

1. **UDP Reception**: Plugin listens for UDP broadcasts on port 50222
2. **Message Parsing**: JSON messages are parsed into structured data
3. **Data Publishing**: Parsed data is published to Waggle message stream
4. **Error Handling**: Invalid messages are logged but don't stop operation

### Publishing Throttling

The plugin implements intelligent throttling to prevent overwhelming the Waggle message stream:

- **Configurable Interval**: Set via `--publish-interval` (default: 60 seconds)
- **Per-Message Type**: Each message type (obs_st, rapid_wind, hub_status) is throttled independently
- **Continuous Reception**: All UDP messages are received and parsed immediately
- **Throttled Publishing**: Data is only published to Waggle if the configured interval has elapsed
- **Latest Data**: The most recent data is always published (not averaged or aggregated)

**Example**: With `--publish-interval 60`:
- Tempest may send rapid_wind updates every 3 seconds
- Plugin receives and parses all updates
- Plugin publishes to Waggle only once per minute (most recent value)
- This prevents excessive message volume while maintaining data freshness

## Message Types

### obs_st (Observation Station)
- Comprehensive weather observations
- Updated every few minutes
- Includes wind, temperature, humidity, pressure, precipitation, lightning

### rapid_wind
- High-frequency wind updates
- Updated every few seconds
- Includes instant wind speed and direction

### hub_status
- Hub system information
- Includes firmware, uptime, signal strength

## Development

### Building from Source

```bash
git clone <repository>
cd tempest-plugin
docker build -t tempest-weather-plugin .
```

### Testing

```bash
# Test with debug output
python3 main.py --debug

# Test with custom port
python3 main.py --udp-port 50223 --debug
```

## License

MIT License - see LICENSE file for details.

## Development

For developers working on this plugin, see [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Development workflow and best practices
- Documentation standards and requirements
- Git workflow and commit guidelines
- Code quality standards
- Testing and deployment procedures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following [DEVELOPMENT.md](DEVELOPMENT.md) guidelines
4. Update README.md, CHANGES.md, and TODO.md as needed
5. Test thoroughly
6. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the main waggle-davis project documentation
- Open an issue on the project repository

