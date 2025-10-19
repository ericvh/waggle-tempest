# Waggle-Tempest Change Log

## 2025-10-12 - Add GitHub Multi-Architecture Docker Build Workflow

### Enhancement: Automated Multi-Arch Docker Builds ✅

**What was added**:
- Created GitHub Actions workflow for automated multi-architecture Docker builds
- Added support for building and publishing images for both amd64 and arm64 architectures
- Integrated with GitHub Container Registry (GHCR) for automatic image publishing
- Added comprehensive build metadata and artifact attestation

**GitHub Workflow Features**:
- **Multi-architecture builds**: Automatically builds for linux/amd64 and linux/arm64
- **Automated publishing**: Pushes to GitHub Container Registry on main branch pushes and tags
- **Smart tagging**: Uses semantic versioning, branch names, and commit SHA for tags
- **Build caching**: Utilizes GitHub Actions cache for faster builds
- **Security**: Includes build provenance attestation for supply chain security
- **Comprehensive output**: Generates detailed build summaries with usage examples

**Workflow Triggers**:
- Push to `main` branch (builds and publishes)
- Tag creation starting with `v*` (builds and publishes semantic versions)
- Pull requests to `main` (builds only, for testing)

**Files added**:
- `.github/workflows/docker-build.yml` - Complete multi-arch build and publish workflow
- `.dockerignore` - Optimized Docker build context excluding unnecessary files

**Files modified**:
- `README.md` - Updated installation and usage sections to include GitHub Container Registry
- Added documentation for multi-architecture image usage and examples

**Registry and Image Information**:
- **Registry**: `ghcr.io`
- **Image**: `ghcr.io/[USERNAME]/waggle-tempest`
- **Architectures**: amd64, arm64
- **Tags**: `latest`, `main`, semantic versions (v1.0.0), commit-based tags

**Benefits**:
- **Cross-platform compatibility**: Runs on both Intel/AMD and ARM64 systems
- **Automated deployment**: No manual build steps required
- **Version management**: Automatic semantic versioning support
- **Security**: Build attestation and provenance tracking
- **Developer experience**: Easy pull and run for any supported architecture

**Usage**:
```bash
# Pull latest multi-arch image
docker run --network host ghcr.io/[USERNAME]/waggle-tempest:latest
```

---

## 2025-10-12 - Add Syntax Checking to Development Workflow

### Enhancement: Automated Syntax Checking ✅

**What was added**:
- Added comprehensive syntax checking requirements to development workflow
- Created automated `check-syntax.sh` script for consistent syntax validation
- Updated DEVELOPMENT.md with syntax checking procedures and requirements

**Syntax Checking Features**:
- Python syntax validation using `py_compile`
- Import testing (handles development environments gracefully)
- Code quality checks (long lines, print statements, TODO comments)
- Optional flake8 linting when available
- File permission verification
- Required file presence validation

**Development Workflow Updates**:
- Added syntax checks as **first step** in pre-commit checklist
- Updated Quick Reference to include syntax checking
- Established automated script usage for consistency

**Files added**:
- `check-syntax.sh` - Automated syntax checking script (executable)

**Files modified**:
- `DEVELOPMENT.md` - Added syntax checking section with requirements and procedures
- Updated development checklist to prioritize syntax validation

**Benefits**:
- Catches syntax errors before commits
- Ensures code quality standards
- Provides consistent checking across environments
- Handles development vs production environment differences
- Automated validation reduces manual errors

**Usage**:
```bash
./check-syntax.sh  # Run comprehensive syntax checks
```

---

## 2025-10-12 - Add Development Guide and Best Practices

### Enhancement: DEVELOPMENT.md Documentation ✅

**What was added**:
- Created comprehensive DEVELOPMENT.md with best practices
- Documented development workflow and standards
- Established documentation update requirements

**Content includes**:
- Documentation requirements (README.md, CHANGES.md, TODO.md updates)
- Git workflow and commit message standards
- Code quality guidelines
- File organization standards
- Development checklist
- Waggle integration standards
- Environment and deployment guidelines
- Maintenance procedures

**Key Standards Established**:
1. **Always update README.md** for user-facing changes
2. **Always update CHANGES.md** for detailed changelog entries
3. **Always maintain TODO.md** with current work status
4. **Always commit changes** with comprehensive messages
5. **Update in order**: Code → README → CHANGES → TODO → Git commit

**Benefits**:
- Ensures consistent project maintenance
- Establishes clear development workflow
- Documents professional best practices
- Provides quick reference for developers

**Files added**:
- `DEVELOPMENT.md` - Complete development guide (new file)

---

## 2025-10-12 - Fix Plugin Initialization

### Bugfix: Pass Config to Plugin() Constructor ✅

**Issue**: Plugin() constructor requires config parameter
**Error**: `TypeError: __init__() missing 1 required positional argument: 'config'`

**Fix**: Pass empty config dict to Plugin constructor:
```python
with Plugin({}) as plugin:
    # Uses default configuration
```

**Changes**:
- `main.py` line 314: Changed `Plugin()` to `Plugin({})` 

---

## 2025-10-11 - Refactor to Plugin Context Manager Pattern

### Refactor: Use `with Plugin() as plugin:` Pattern ✅

**What changed**:
- Removed global `plugin` variable
- Refactored main() to use `with Plugin() as plugin:` context manager
- Moved publishing logic into main() as nested function inside with block
- Publishing function now accesses plugin via closure (no global state)
- Updated UDP listener to accept publish_callback parameter
- Removed global plugin references throughout codebase

**Benefits**:
- **Proper Resource Management**: Context manager ensures plugin cleanup on exit
- **Better Encapsulation**: Publishing logic has direct access to plugin via closure
- **Thread Safety**: Eliminates global plugin state
- **Cleaner Code**: Publishing function nested in appropriate scope
- **Best Practice**: Follows Python context manager patterns

**Code Structure**:
```python
def main():
    # ... initialization ...
    
    with Plugin() as plugin:
        # Define publishing as nested function with access to plugin
        def publish_tempest_data(parsed_data, msg_type, force=False):
            # Has access to plugin via closure
            plugin.publish(...)
        
        # Start UDP listener with publish callback
        udp_thread = threading.Thread(
            target=tempest_udp_listener,
            args=(logger, publish_tempest_data, udp_port)
        )
        
        # Main loop inside with block
        while True:
            ...
```

**Changes**:
- `main.py` lines 33-35: Removed global plugin variable
- `main.py` lines 149-150: Removed standalone publish_tempest_data function
- `main.py` lines 154: Updated tempest_udp_listener to accept publish_callback
- `main.py` lines 312-526: Refactored main() with context manager and nested publishing function

---

## 2025-10-11 - Waggle Publishing Metadata Enhancement

### Enhancement: Comprehensive Metadata with Scope and Sensor Information ✅

**What was added**:
- Added `scope="beehive"` parameter to all plugin.publish() calls
- Added `sensor="tempest-weather-station"` to all metadata dictionaries
- Added `missing=-9999.0` field to indicate missing/invalid values (numeric) or "unknown" (string)
- Added explicit timestamps using `datetime.now(timezone.utc)` for all publications
- Aligned with waggle-davis-wind-sensor plugin methodology for consistency

**Metadata Structure** (following waggle-davis pattern):
```python
plugin.publish("tempest.wind.speed.avg", value,
             timestamp=timestamp,
             scope="beehive",
             meta={"sensor": "tempest-weather-station",
                   "units": "knots",
                   "description": "Tempest average wind speed",
                   "source": "obs_st",
                   "missing": -9999.0})
```

**Key Changes**:
1. **Scope**: All data published to "beehive" scope (central server for analysis)
2. **Sensor**: Identifies data source as "tempest-weather-station"
3. **Missing Value**: Standard indicator for invalid/missing data (-9999.0 numeric, "unknown" string)
4. **Timestamps**: Explicit UTC timestamps for all measurements
5. **Consistency**: Follows established Waggle ecosystem patterns

**Benefits**:
- Better data organization in Waggle ecosystem
- Proper scoping for beehive vs node data
- Standard missing value indicator for data quality
- Improved metadata for downstream analysis
- Consistency with other Waggle weather plugins

**All publish() calls updated**:
- Wind data (lull/avg/gust speeds, direction, instant readings)
- Environmental data (temperature, humidity, pressure)
- Light data (illuminance, UV index, solar radiation)
- Precipitation data (since report, daily)
- Lightning data (distance, strike count)
- System data (battery, report interval)
- Hub status (firmware, uptime, RSSI)
- Plugin status (heartbeat, errors, shutdown)

**Code Location**:
- `main.py` lines 172-393: Updated publish_tempest_data() function
- `main.py` lines 450-461: Updated UDP listener error status
- `main.py` lines 618-629: Updated cleanup/shutdown status

---

## 2025-10-11 - Environment Variable Support

### Enhancement: Complete Environment Variable Configuration ✅

**What was added**:
- All command-line arguments now support environment variable configuration
- Environment variables can be used as defaults, with CLI args taking precedence
- Added visual indicators showing which env vars are active at startup
- Enhanced help text to document environment variable names

**Environment Variables** (4 total):
- `TEMPEST_UDP_PORT` - UDP port (integer, default: 50222)
- `TEMPEST_PUBLISH_INTERVAL` - Publish interval in seconds (integer, default: 60)
- `TEMPEST_DEBUG` - Debug mode (boolean: true/1/yes/on)
- `TEMPEST_NO_FIREWALL` - Skip firewall warnings (boolean: true/1/yes/on)

**Configuration Priority**:
1. Command-line arguments (highest)
2. Environment variables
3. Built-in defaults (lowest)

**Code Changes**:

**main.py Lines 318-361**: Enhanced `parse_args()` function
- Added `env_bool()` helper for boolean environment variable parsing
- Read environment variables with `os.getenv()` before setting argument defaults
- Updated help text to show corresponding environment variable names
- Added epilog documenting all environment variables

**main.py Lines 387-403**: Startup configuration display
- Shows all configuration values at startup
- Added 📌 indicator when environment variables are active
- Lists which specific env vars are being used
- Helps users verify configuration source

**README.md Updates**:
- Added comprehensive configuration tables for env vars and CLI args
- Documented boolean value parsing (true/1/yes/on)
- Added configuration priority explanation
- Enhanced Docker examples showing env var usage
- Added mixed configuration examples

**Benefits**:
- Better Docker/Kubernetes integration (env vars preferred in containers)
- Easier CI/CD pipeline configuration
- No need to modify command-line args in scripts
- More flexible deployment options
- Clear visibility of active configuration

**Example Usage**:
```bash
# Via environment variables
export TEMPEST_DEBUG=true
export TEMPEST_PUBLISH_INTERVAL=30
python3 main.py

# Docker with env vars
docker run --network host \
  -e TEMPEST_DEBUG=true \
  -e TEMPEST_PUBLISH_INTERVAL=30 \
  tempest-weather-plugin

# Override env vars with CLI args
TEMPEST_DEBUG=false python3 main.py --debug  # debug=true (CLI wins)
```

---

## 2025-10-11 - Initial Implementation and Waggle Publishing

### Major Features Implemented

#### 1. Tempest Data Publishing to Waggle ✅
**Status**: Complete and functional

**What was done**:
- Implemented full Waggle publishing functionality in `publish_tempest_data()` function
- Publishes comprehensive weather data from Tempest station to Waggle message stream
- Added support for all major Tempest message types:
  - `obs_st`: Comprehensive weather observations
  - `rapid_wind`: High-frequency wind updates
  - `hub_status`: System status information

**Published Topics** (20+ data points):
- Wind: speed (lull/avg/gust/instant), direction
- Environmental: temperature, humidity, pressure
- Light: illuminance, UV index, solar radiation
- Precipitation: rain accumulation (report/daily)
- Lightning: distance, strike count
- System: battery, report interval, hub firmware, uptime, RSSI
- Status: plugin health indicator

#### 2. Publish Interval Throttling ⚡
**Problem**: Original code had `--publish-interval` parameter but wasn't using it

**Solution**:
- Added `last_publish_times` dictionary to track last publish time per message type
- Implemented per-message-type throttling in `publish_tempest_data()`
- Added time-elapsed checking before publishing
- Configured default 60-second interval to prevent message overflow

**Benefits**:
- Prevents overwhelming Waggle message stream
- Reduces network/storage load
- Maintains data freshness (always publishes latest value)
- Independent throttling for obs_st, rapid_wind, and hub_status

#### 3. Configuration Improvements 🔧

**Command-Line Arguments**:
- Connected `--publish-interval` argument to actual publishing logic
- Made `--udp-port` configurable throughout the codebase
- Passed UDP port to listener thread properly

**Global State Management**:
- Added `publish_interval` global variable
- Added `last_publish_times` tracking dictionary
- Properly initialized in `main()` function

#### 4. Enhanced Logging 📊

**Improved visibility**:
- Added 📥 indicator when UDP messages are received
- Added 📡 indicator when data is published to Waggle
- Enhanced publish messages with key data values
- Debug messages explain throttling decisions

**Examples**:
```
📥 Received obs_st message from 192.168.1.50
📡 Published obs_st data: Wind 12.3 kt @ 245°, Temp 18.5°C, RH 65%
Skipping rapid_wind publish - only 3.2s elapsed (need 60s)
```

### Code Changes

#### main.py

**Lines 28-36**: Added global state for publishing control
```python
# Global plugin instance and publishing control
plugin = None
last_publish_times = {}  # Track last publish time for each message type
publish_interval = 60  # Default publish interval in seconds
```

**Lines 151-171**: Implemented throttling logic in `publish_tempest_data()`
- Added `force` parameter for future use
- Check elapsed time since last publish
- Skip publishing if interval not met
- Update last publish time on successful publish

**Lines 221, 232, 243**: Enhanced logging with data summaries
- obs_st: Shows wind, temperature, humidity
- rapid_wind: Shows instant wind values
- hub_status: Shows firmware, uptime, RSSI

**Line 256**: Made UDP port configurable in listener
```python
def tempest_udp_listener(logger, udp_port=UDP_PORT):
```

**Line 272**: Added debug logging for received messages
```python
logger.debug(f"📥 Received {msg_type} message from {addr[0]}")
```

**Line 288**: Clarified comment about throttled publishing
```python
# Attempt to publish the data (will be throttled based on publish_interval)
```

**Lines 349-361**: Properly initialized publish_interval from args
```python
global plugin, publish_interval
# ...
publish_interval = args.publish_interval
```

**Line 392**: Pass UDP port to listener thread
```python
args=(logger, args.udp_port),
```

### Documentation Changes

#### README.md

**Lines 234-248**: Added "Publishing Throttling" section
- Explains how throttling works
- Documents configuration options
- Provides example with timing
- Clarifies benefits (prevents overflow while maintaining freshness)

### Technical Details

#### Publishing Flow
1. **UDP Reception**: Continuous listening on port 50222 (or configured port)
2. **Immediate Parsing**: All messages parsed in real-time
3. **Throttled Publishing**: Only publish if interval elapsed
4. **Latest Data**: Most recent parsed data published (no averaging)

#### Throttling Mechanism
- Per-message-type tracking (independent intervals)
- Time-based (not count-based)
- Configurable via command-line
- Debug logging for skipped publishes

#### Error Handling
- Invalid messages logged but don't stop operation
- Plugin status published on errors
- Graceful degradation on connection issues

### Testing Recommendations

Before deployment, verify:
1. Tempest UDP broadcasts are received
2. Data is published to Waggle at correct intervals
3. Throttling works correctly for each message type
4. Debug logging shows expected behavior
5. Firewall rules allow UDP port 50222

### Configuration Examples

**Default (60-second intervals)**:
```bash
python3 main.py
```

**Faster updates (30-second intervals)**:
```bash
python3 main.py --publish-interval 30
```

**Debug mode with custom port**:
```bash
python3 main.py --debug --udp-port 50223 --publish-interval 45
```

### Deployment Notes

- Requires `waggle>=0.7.0` package
- Uses only standard library (except waggle)
- Requires host networking or UDP broadcast access
- Default publish interval (60s) recommended for production
- Can run alongside waggle-davis without conflicts

### Known Limitations

- No data aggregation (publishes latest value only)
- No historical buffering (real-time only)
- No automatic UDP reconnection (runs continuously)
- No multi-station support (single Tempest per instance)

### Future Work

See TODO.md for potential enhancements including:
- Data aggregation options
- Historical buffering
- Prometheus metrics
- Unit/integration tests
- Configuration file support

---

**Summary**: The Tempest Weather Station Waggle Plugin is now fully functional with proper data publishing, intelligent throttling, and comprehensive logging. Ready for deployment and testing with actual Tempest hardware.

