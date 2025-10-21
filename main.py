#!/usr/bin/env python3

"""
Tempest Weather Station Waggle Plugin
=====================================

A Waggle plugin that receives TCP length-prefixed messages or UDP broadcasts from 
a local Tempest weather station and publishes the data to the Waggle message stream.

This plugin extracts the Tempest functionality from the main waggle-davis project
and provides it as a standalone service for publishing Tempest weather data.

Default protocol is TCP with length-prefixed JSON messages for improved reliability.
UDP broadcast mode is also supported for backward compatibility.
"""

import argparse
import logging
import json
import os
import socket
import threading
import time
from datetime import datetime, timezone
from waggle.plugin import Plugin


# Tempest network configuration
UDP_PORT = 50222
TCP_PORT = 50222
DEFAULT_PROTOCOL = "tcp"  # TCP is now the default protocol

# Global Tempest data storage
tempest_data_lock = threading.Lock()
latest_tempest_raw_by_type = {}
latest_tempest_parsed_by_type = {}

# Global plugin instance and publishing control
last_publish_times = {}  # Track last publish time for each message type
publish_interval = 60  # Default publish interval in seconds


# ---------------- Unit Conversion Functions ----------------
def c_to_f(c): 
    return None if c is None else (c * 9/5) + 32

def mps_to_kt(m): 
    return None if m is None else m * 1.943844

def hpa_to_inhg(h): 
    return None if h is None else h * 0.0295299830714

def mm_to_in(mm): 
    return None if mm is None else mm / 25.4


def get_nanosecond_timestamp(tempest_timestamp=None):
    """
    Convert timestamp to nanoseconds since epoch as required by Waggle.
    
    Args:
        tempest_timestamp: Optional Tempest timestamp (epoch seconds)
                          If None, uses current time
    
    Returns:
        int: Nanoseconds since epoch
    """
    if tempest_timestamp is not None:
        # Tempest timestamps are in seconds since epoch
        timestamp_ns = int(tempest_timestamp * 1_000_000_000)
    else:
        # Use current time
        timestamp_ns = int(time.time() * 1_000_000_000)
    
    return timestamp_ns


# ---------------- Tempest Message Parsers ----------------
PRECIP_TYPES = {
    0: "none",
    1: "rain", 
    2: "hail",
    3: "snow",
}

def parse_obs_st(msg):
    """Parse Tempest device observation messages"""
    obs = msg.get("obs", [[]])[0] if msg.get("obs") else []
    if not obs:
        return {"type": "obs_st", "error": "empty obs"}

    return {
        "timestamp": obs[0],
        "wind": {
            "lull_mps": obs[1], "lull_kt": mps_to_kt(obs[1]),
            "avg_mps": obs[2],  "avg_kt": mps_to_kt(obs[2]),
            "gust_mps": obs[3], "gust_kt": mps_to_kt(obs[3]),
            "direction_deg": obs[4],
            "sample_interval_s": obs[5],
        },
        "pressure": {
            "hpa": obs[6],
            "inHg": hpa_to_inhg(obs[6]),
        },
        "temperature": {
            "c": obs[7],
            "f": c_to_f(obs[7]),
        },
        "humidity_percent": obs[8],
        "light": {
            "illuminance_lux": obs[9],
            "uv_index": obs[10],
            "solar_radiation_wm2": obs[11],
        },
        "rain": {
            "since_report_mm": obs[12],
            "since_report_in": mm_to_in(obs[12]),
            "precipitation_type": PRECIP_TYPES.get(obs[13], "unknown"),
            "local_day_mm": obs[18] if len(obs) > 18 else None,
            "local_day_in": mm_to_in(obs[18]) if len(obs) > 18 else None,
        },
        "lightning": {
            "avg_distance_km": obs[14],
            "strike_count": obs[15],
        },
        "battery_v": obs[16],
        "report_interval_min": obs[17],
        "meta": {
            "device_sn": msg.get("serial_number"),
            "hub_sn": msg.get("hub_sn"),
            "received_at": int(time.time()),
        },
    }

def parse_rapid_wind(msg):
    """Parse rapid wind messages for instant wind readings"""
    ob = msg.get("ob", [])
    if len(ob) < 3:
        return {"type": "rapid_wind", "error": "bad ob"}
    return {
        "timestamp": ob[0],
        "wind": {
            "instant_mps": ob[1],
            "instant_kt": mps_to_kt(ob[1]),
            "direction_deg": ob[2],
        },
        "meta": {
            "device_sn": msg.get("serial_number"),
            "hub_sn": msg.get("hub_sn"),
            "received_at": int(time.time()),
        },
    }

def parse_hub_status(msg):
    """Parse hub status messages"""
    return {
        "firmware": msg.get("firmware_revision"),
        "uptime_s": msg.get("uptime"),
        "rssi": msg.get("rssi"),
        "timestamp": msg.get("time"),
        "meta": {
            "hub_sn": msg.get("serial_number"),
            "received_at": int(time.time()),
        },
    }

# Message type parsers
TEMPEST_PARSERS = {
    "obs_st": parse_obs_st,
    "rapid_wind": parse_rapid_wind,
    "hub_status": parse_hub_status,
}


# ---------------- Data Publishing Functions ----------------
# Publishing logic is now inside main() function within the Plugin context manager


# ---------------- UDP Listener ----------------
def tempest_udp_listener(logger, publish_callback, udp_port=UDP_PORT):
    """UDP listener thread for Tempest broadcasts"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", udp_port))
        
        logger.info(f"🌐 Tempest UDP listener started on port {udp_port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8"))
                
                msg_type = msg.get("type", "unknown")
                
                logger.debug(f"📥 Received {msg_type} message from {addr[0]}")
                
                # Store the raw message by type
                with tempest_data_lock:
                    latest_tempest_raw_by_type[msg_type] = msg
                    
                    # If we have a parser for this type, also store parsed
                    parser = TEMPEST_PARSERS.get(msg_type)
                    if parser:
                        try:
                            parsed_data = parser(msg)
                            latest_tempest_parsed_by_type[msg_type] = {
                                "type": msg_type,
                                "data": parsed_data
                            }
                            
                            # Attempt to publish the data (will be throttled based on publish_interval)
                            publish_callback(parsed_data, msg_type)
                            
                        except Exception as e:
                            logger.error(f"Error parsing {msg_type} message: {e}")
                            # Skip parsing errors but continue listening
                    else:
                        # If no parser, remove any stale parsed entry
                        if msg_type in latest_tempest_parsed_by_type:
                            del latest_tempest_parsed_by_type[msg_type]
                        logger.debug(f"Received unknown message type: {msg_type}")
                            
            except json.JSONDecodeError:
                # Skip non-JSON packets
                continue
            except Exception as e:
                # Log UDP errors but continue listening
                logger.error(f"UDP listener error: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to start Tempest UDP listener: {e}")
        # Error will be handled by main function


# ---------------- TCP Listener ----------------
def tempest_tcp_listener(logger, publish_callback, tcp_port=TCP_PORT):
    """TCP listener thread for Tempest length-prefixed messages"""
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("0.0.0.0", tcp_port))
        server_sock.listen(5)
        
        logger.info(f"🌐 Tempest TCP listener started on port {tcp_port}")
        logger.info("📡 Waiting for TCP connections with length-prefixed JSON messages...")
        
        while True:
            try:
                # Accept incoming connections
                client_sock, addr = server_sock.accept()
                logger.debug(f"📡 Accepted TCP connection from {addr[0]}:{addr[1]}")
                
                # Handle messages from this client
                handle_tcp_client(client_sock, addr, logger, publish_callback)
                
            except Exception as e:
                logger.error(f"TCP listener error: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to start Tempest TCP listener: {e}")
        # Error will be handled by main function


def handle_tcp_client(client_sock, addr, logger, publish_callback):
    """Handle messages from a TCP client connection"""
    try:
        while True:
            # Read length prefix (4 bytes, big-endian)
            length_data = recv_exactly(client_sock, 4, logger)
            if not length_data:
                break
                
            # Unpack length
            msg_length = int.from_bytes(length_data, byteorder='big')
            
            if msg_length <= 0 or msg_length > 65535:  # Reasonable limits
                logger.warning(f"Invalid message length: {msg_length} from {addr[0]}")
                break
            
            # Read the actual message
            msg_data = recv_exactly(client_sock, msg_length, logger)
            if not msg_data:
                break
                
            try:
                # Parse JSON message
                msg = json.loads(msg_data.decode("utf-8"))
                msg_type = msg.get("type", "unknown")
                
                logger.debug(f"📥 Received {msg_type} TCP message from {addr[0]} ({msg_length} bytes)")
                
                # Store the raw message by type
                with tempest_data_lock:
                    latest_tempest_raw_by_type[msg_type] = msg
                    
                    # If we have a parser for this type, also store parsed
                    parser = TEMPEST_PARSERS.get(msg_type)
                    if parser:
                        try:
                            parsed_data = parser(msg)
                            latest_tempest_parsed_by_type[msg_type] = {
                                "type": msg_type,
                                "data": parsed_data
                            }
                            
                            # Attempt to publish the data (will be throttled based on publish_interval)
                            publish_callback(parsed_data, msg_type)
                            
                        except Exception as e:
                            logger.error(f"Error parsing {msg_type} message: {e}")
                            # Skip parsing errors but continue listening
                    else:
                        # If no parser, remove any stale parsed entry
                        if msg_type in latest_tempest_parsed_by_type:
                            del latest_tempest_parsed_by_type[msg_type]
                        logger.debug(f"Received unknown message type: {msg_type}")
                        
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {addr[0]}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing TCP message from {addr[0]}: {e}")
                continue
                
    except Exception as e:
        logger.debug(f"TCP client {addr[0]} disconnected: {e}")
    finally:
        try:
            client_sock.close()
        except:
            pass


def recv_exactly(sock, num_bytes, logger):
    """Receive exactly num_bytes from socket"""
    data = b""
    while len(data) < num_bytes:
        try:
            chunk = sock.recv(num_bytes - len(data))
            if not chunk:
                return None  # Connection closed
            data += chunk
        except socket.timeout:
            logger.warning("TCP receive timeout")
            return None
        except Exception as e:
            logger.error(f"TCP receive error: {e}")
            return None
    return data


# ---------------- Command Line Arguments ----------------
def parse_args():
    """Parse command line arguments with environment variable support"""
    # Helper function to check environment variables for boolean flags
    def env_bool(env_var):
        """Convert environment variable to boolean"""
        val = os.getenv(env_var, "").lower()
        return val in ("true", "1", "yes", "on")
    
    # Get defaults from environment variables or use hardcoded defaults
    default_protocol = os.getenv("TEMPEST_PROTOCOL", DEFAULT_PROTOCOL).lower()
    default_tcp_port = int(os.getenv("TEMPEST_TCP_PORT", TCP_PORT))
    default_udp_port = int(os.getenv("TEMPEST_UDP_PORT", UDP_PORT))
    default_debug = env_bool("TEMPEST_DEBUG")
    default_publish_interval = int(os.getenv("TEMPEST_PUBLISH_INTERVAL", "60"))
    default_no_firewall = env_bool("TEMPEST_NO_FIREWALL")
    
    parser = argparse.ArgumentParser(
        description="Tempest Weather Station Waggle Plugin - publishes Tempest data to Waggle stream",
        epilog="All arguments can be set via environment variables: TEMPEST_PROTOCOL, TEMPEST_TCP_PORT, "
               "TEMPEST_UDP_PORT, TEMPEST_DEBUG, TEMPEST_PUBLISH_INTERVAL, TEMPEST_NO_FIREWALL"
    )
    parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default=default_protocol,
        help=f"Protocol to use for receiving data (default: {DEFAULT_PROTOCOL}, env: TEMPEST_PROTOCOL)"
    )
    parser.add_argument(
        "--tcp-port", 
        type=int,
        default=default_tcp_port,
        help=f"TCP port to listen on for length-prefixed messages (default: {TCP_PORT}, env: TEMPEST_TCP_PORT)"
    )
    parser.add_argument(
        "--udp-port", 
        type=int,
        default=default_udp_port, 
        help=f"UDP port to listen for broadcasts (default: {UDP_PORT}, env: TEMPEST_UDP_PORT)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        default=default_debug,
        help="Enable debug output (env: TEMPEST_DEBUG=true)"
    )
    parser.add_argument(
        "--publish-interval", 
        type=int, 
        default=default_publish_interval, 
        help="Minimum interval between data publications in seconds (default: 60, env: TEMPEST_PUBLISH_INTERVAL)"
    )
    parser.add_argument(
        "--no-firewall", 
        action="store_true",
        default=default_no_firewall, 
        help="Skip firewall setup warnings (env: TEMPEST_NO_FIREWALL=true)"
    )
    return parser.parse_args()


# ---------------- Main Function ----------------
def main():
    """Main function"""
    global publish_interval
    
    args = parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Set global publish interval from args
    publish_interval = args.publish_interval
    
    logger.info("🌤️  Starting Tempest Weather Station Waggle Plugin")
    logger.info("=" * 60)
    
    # Show configuration with source indicators
    env_indicators = []
    if os.getenv("TEMPEST_PROTOCOL"):
        env_indicators.append("PROTOCOL")
    if os.getenv("TEMPEST_TCP_PORT"):
        env_indicators.append("TCP_PORT")
    if os.getenv("TEMPEST_UDP_PORT"):
        env_indicators.append("UDP_PORT")
    if os.getenv("TEMPEST_PUBLISH_INTERVAL"):
        env_indicators.append("PUBLISH_INTERVAL")
    if os.getenv("TEMPEST_DEBUG"):
        env_indicators.append("DEBUG")
    if os.getenv("TEMPEST_NO_FIREWALL"):
        env_indicators.append("NO_FIREWALL")
    
    logger.info(f"Protocol: {args.protocol.upper()}")
    if args.protocol == "tcp":
        logger.info(f"TCP Port: {args.tcp_port}")
    else:
        logger.info(f"UDP Port: {args.udp_port}")
    logger.info(f"Publish Interval: {args.publish_interval} seconds")
    logger.info(f"Debug Mode: {args.debug}")
    logger.info(f"No Firewall Check: {args.no_firewall}")
    if env_indicators:
        logger.info(f"📌 Using environment variables: {', '.join(env_indicators)}")
    logger.info("")
    
    # Check port accessibility
    if not args.no_firewall:
        port_to_check = args.tcp_port if args.protocol == "tcp" else args.udp_port
        logger.info(f"🔍 Checking {args.protocol.upper()} port accessibility...")
        try:
            if args.protocol == "tcp":
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(("0.0.0.0", port_to_check))
            test_sock.close()
            logger.info(f"✓ {args.protocol.upper()} port {port_to_check} is accessible")
        except Exception as e:
            logger.warning(f"⚠️  {args.protocol.upper()} port {port_to_check} binding failed: {e}")
            if args.protocol == "tcp":
                logger.warning("💡 You may need to configure firewall rules:")
                logger.warning(f"   sudo iptables -I INPUT -p tcp --dport {port_to_check} -j ACCEPT")
            else:
                logger.warning("💡 You may need to configure firewall rules:")
                logger.warning(f"   sudo iptables -I INPUT -p udp --dport {port_to_check} -j ACCEPT")
                logger.warning("   Or use the firewall-opener container from the main project")
    
    # Use Plugin context manager for proper lifecycle management
    # Pass empty config dict for default configuration
    with Plugin({}) as plugin:
        # Define publishing function as nested function with access to plugin via closure
        def publish_tempest_data(parsed_data, msg_type, force=False):
            """Publish Tempest data to Waggle message stream"""
            global last_publish_times, publish_interval
            
            # Check if enough time has elapsed since last publish (unless forced)
            if not force:
                current_time = time.time()
                last_publish = last_publish_times.get(msg_type, 0)
                time_elapsed = current_time - last_publish
                
                if time_elapsed < publish_interval:
                    logger.debug(f"Skipping {msg_type} publish - only {time_elapsed:.1f}s elapsed (need {publish_interval}s)")
                    return
                
                # Update last publish time
                last_publish_times[msg_type] = current_time
            
            try:
                if msg_type == "obs_st" and "error" not in parsed_data:
                    # Publish comprehensive weather observations
                    obs = parsed_data
                    timestamp = get_nanosecond_timestamp(obs.get("timestamp"))
                    
                    # Wind data
                    plugin.publish("tempest.wind.speed.lull", obs["wind"]["lull_kt"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "knots", 
                                       "description": "Tempest wind lull speed", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.wind.speed.avg", obs["wind"]["avg_kt"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "knots", 
                                       "description": "Tempest average wind speed", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.wind.speed.gust", obs["wind"]["gust_kt"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "knots", 
                                       "description": "Tempest wind gust speed", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.wind.direction", obs["wind"]["direction_deg"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "degrees", 
                                       "description": "Tempest wind direction", "source": "obs_st", "missing": -9999.0})
                    
                    # Environmental data
                    plugin.publish("tempest.pressure", obs["pressure"]["hpa"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "hPa", 
                                       "description": "Tempest barometric pressure", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.temperature", obs["temperature"]["c"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "celsius", 
                                       "description": "Tempest air temperature", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.humidity", obs["humidity_percent"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "percent", 
                                       "description": "Tempest relative humidity", "source": "obs_st", "missing": -9999.0})
                    
                    # Light data
                    plugin.publish("tempest.light.illuminance", obs["light"]["illuminance_lux"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "lux", 
                                       "description": "Tempest illuminance", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.light.uv_index", obs["light"]["uv_index"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "index", 
                                       "description": "Tempest UV index", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.light.solar_radiation", obs["light"]["solar_radiation_wm2"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "W/m²", 
                                       "description": "Tempest solar radiation", "source": "obs_st", "missing": -9999.0})
                    
                    # Precipitation data
                    plugin.publish("tempest.rain.since_report", obs["rain"]["since_report_mm"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "mm", 
                                       "description": "Tempest rain since report", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.rain.daily", obs["rain"]["local_day_mm"] or 0, 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "mm", 
                                       "description": "Tempest daily rainfall", "source": "obs_st", "missing": -9999.0})
                    
                    # Lightning data
                    plugin.publish("tempest.lightning.distance", obs["lightning"]["avg_distance_km"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "km", 
                                       "description": "Tempest lightning distance", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.lightning.count", obs["lightning"]["strike_count"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "count", 
                                       "description": "Tempest lightning strike count", "source": "obs_st", "missing": -9999.0})
                    
                    # Battery and system data
                    plugin.publish("tempest.battery", obs["battery_v"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "volts", 
                                       "description": "Tempest battery voltage", "source": "obs_st", "missing": -9999.0})
                    plugin.publish("tempest.report_interval", obs["report_interval_min"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "minutes", 
                                       "description": "Tempest report interval", "source": "obs_st", "missing": -9999.0})
                    
                    logger.info(f"📡 Published obs_st data: Wind {obs['wind']['avg_kt']:.1f} kt @ {obs['wind']['direction_deg']:.0f}°, Temp {obs['temperature']['c']:.1f}°C, RH {obs['humidity_percent']:.0f}%")
                    
                elif msg_type == "rapid_wind" and "error" not in parsed_data:
                    # Publish rapid wind data (most recent wind readings)
                    wind = parsed_data["wind"]
                    timestamp = get_nanosecond_timestamp(parsed_data.get("timestamp"))
                    
                    plugin.publish("tempest.wind.speed.instant", wind["instant_kt"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "knots", 
                                       "description": "Tempest instant wind speed", "source": "rapid_wind", "missing": -9999.0})
                    plugin.publish("tempest.wind.direction.instant", wind["direction_deg"], 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "degrees", 
                                       "description": "Tempest instant wind direction", "source": "rapid_wind", "missing": -9999.0})
                    
                    logger.info(f"📡 Published rapid_wind data: {wind['instant_kt']:.1f} kt @ {wind['direction_deg']:.0f}°")
                    
                elif msg_type == "hub_status" and "error" not in parsed_data:
                    # Publish hub status data
                    timestamp = get_nanosecond_timestamp(parsed_data.get("timestamp"))
                    
                    plugin.publish("tempest.hub.firmware", parsed_data["firmware"] or "unknown", 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "description": "Tempest hub firmware version", 
                                       "source": "hub_status", "missing": "unknown"})
                    plugin.publish("tempest.hub.uptime", parsed_data["uptime_s"] or 0, 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "seconds", 
                                       "description": "Tempest hub uptime", "source": "hub_status", "missing": -9999.0})
                    plugin.publish("tempest.hub.rssi", parsed_data["rssi"] or 0, 
                                 timestamp=timestamp, scope="beehive",
                                 meta={"sensor": "tempest-weather-station", "units": "dBm", 
                                       "description": "Tempest hub signal strength", "source": "hub_status", "missing": -9999.0})
                    
                    logger.info(f"📡 Published hub_status data: firmware={parsed_data['firmware']}, uptime={parsed_data['uptime_s']}s, RSSI={parsed_data['rssi']}dBm")
                    
                # Always publish a heartbeat/status message
                status_timestamp = get_nanosecond_timestamp()
                plugin.publish("tempest.status", 1, 
                             timestamp=status_timestamp, scope="beehive",
                             meta={"sensor": "tempest-weather-station", 
                                   "description": "Tempest plugin status (1=active, 0=error)", 
                                   "last_update": int(time.time()), "missing": -9999.0})
                
            except Exception as e:
                logger.error(f"Error publishing Tempest data: {e}")
                error_timestamp = get_nanosecond_timestamp()
                plugin.publish("tempest.status", 0, 
                             timestamp=error_timestamp, scope="beehive",
                             meta={"sensor": "tempest-weather-station", 
                                   "description": "Tempest plugin status (1=active, 0=error)", 
                                   "error": str(e), "missing": -9999.0})
        
        # Start appropriate listener thread based on protocol
        if args.protocol == "tcp":
            logger.info("🌐 Starting Tempest TCP listener thread...")
            listener_thread = threading.Thread(
                target=tempest_tcp_listener, 
                args=(logger, publish_tempest_data, args.tcp_port),
                daemon=True
            )
            wait_msg = "⏳ Waiting for Tempest TCP connections with length-prefixed messages..."
        else:
            logger.info("🌐 Starting Tempest UDP listener thread...")
            listener_thread = threading.Thread(
                target=tempest_udp_listener, 
                args=(logger, publish_tempest_data, args.udp_port),
                daemon=True
            )
            wait_msg = "⏳ Waiting for Tempest UDP broadcasts..."
        
        listener_thread.start()
        
        # Wait for initial data
        logger.info(wait_msg)
        time.sleep(5)  # Give some time for initial data
        
        # Check if we received any data
        with tempest_data_lock:
            if latest_tempest_raw_by_type:
                logger.info(f"✅ Tempest station detected! Received {len(latest_tempest_raw_by_type)} message types:")
                for msg_type in latest_tempest_raw_by_type.keys():
                    logger.info(f"   - {msg_type}")
            else:
                logger.warning("⚠️  No Tempest data received yet")
                logger.info("💡 Troubleshooting:")
                if args.protocol == "tcp":
                    logger.info("   1. Check that Tempest hub is configured to send TCP data")
                    logger.info("   2. Verify TCP connections can be established on the configured port")
                    logger.info(f"   3. Check firewall/router settings for TCP port {args.tcp_port}")
                else:
                    logger.info("   1. Check that Tempest hub is on the same network")
                    logger.info("   2. Verify Tempest station is broadcasting (usually enabled by default)")
                    logger.info(f"   3. Check firewall/router settings for UDP port {args.udp_port}")
                logger.info("   4. Try running with --no-firewall if you've already configured firewall")
        
        logger.info("")
        logger.info("📡 Tempest plugin is running and publishing data to Waggle stream")
        logger.info("🛑 Press Ctrl+C to stop")
        logger.info("")
        
        try:
            # Main loop - just keep the plugin running
            # The listener thread handles all data processing and publishing
            while True:
                time.sleep(60)  # Check every minute
                
                # Periodic status update
                with tempest_data_lock:
                    if latest_tempest_raw_by_type:
                        logger.info(f"📊 Status: Active, {len(latest_tempest_raw_by_type)} message types received")
                    else:
                        logger.warning("📊 Status: No data received from Tempest station")
                        
        except KeyboardInterrupt:
            logger.info("🛑 Tempest plugin stopped by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error in Tempest plugin: {e}")
            raise
        finally:
            # Cleanup
            logger.info("🧹 Cleaning up Tempest plugin...")
            shutdown_timestamp = get_nanosecond_timestamp()
            plugin.publish("tempest.status", 0, 
                         timestamp=shutdown_timestamp, scope="beehive",
                         meta={"sensor": "tempest-weather-station", 
                               "description": "Tempest plugin status (1=active, 0=error)", 
                               "state": "shutdown", "missing": -9999.0})


if __name__ == "__main__":
    main()

