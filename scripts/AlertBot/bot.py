#!/usr/bin/env python3
"""
Alert Bot - Sends multiple messages to a channel with intervals, repeating hourly
Usage: python bot.py [port] [channel_index]
"""

import asyncio
import sys
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from serial.tools import list_ports
from meshcore import MeshCore, EventType

# Configuration
BAUDRATE = 115200
CHANNEL_IDX = 0  # Default to channel 0 (public channel)
MESSAGE_INTERVAL_SECONDS = 15  # 15 seconds between messages
CYCLE_INTERVAL_MINUTES = 60  # 1 hour between message cycles

# Config file path (in same directory as script)
CONFIG_FILE = Path(__file__).parent / ".config.json"
LOG_FILE = Path(__file__).parent / "bot.log"

# Setup logging to both console and file
def setup_logging():
    """Configure logging to both console and file"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logging
logger = setup_logging()

# Messages to send (will be sent with 1 minute intervals)
MESSAGES = [
    "📻 Welkom op het MeshCore netwerk van Kortrijk! Je bent op de juiste plek.",
    "🌐 Help ons het netwerk uitbreiden! Meer nodes = beter bereik voor iedereen.",
    "💬 Stuur af en toe een bericht in dit publieke kanaal, zo weten we dat je er bent!",
    "💬 Join onze Discord: https://discord.gg/kvybAgqnhD en chat met gelijkgestemden",
    "🌍 Bezoek https://radio-actief.be - de actiefste radio community van België",
    "🤖 Deze berichten herhalen zich elke uur."
]

def load_saved_port():
    """Load saved port from config file"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('port', None)
    except (json.JSONDecodeError, IOError):
        pass
    return None

def save_port(port):
    """Save port to config file"""
    try:
        config = {'port': port}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError:
        pass  # Silently fail if we can't save

def list_serial_ports():
    """List all available serial ports"""
    ports = list_ports.comports()
    return ports if ports else []

def select_port(skip_saved=False):
    """Select a serial port, trying saved port first, then interactive selection
    
    Args:
        skip_saved: If True, skip loading saved port (useful for retries)
    """
    # Check if port provided as first argument
    if len(sys.argv) > 1:
        # Check if it looks like a port path (starts with /dev/ or COM)
        arg = sys.argv[1]
        if arg.startswith('/dev/') or arg.startswith('COM') or ':' in arg:
            save_port(arg)  # Save the port for next time
            return arg
    
    # Try loading saved port first (unless we're retrying)
    saved_port = None if skip_saved else load_saved_port()
    if saved_port:
        # Check if saved port is in available ports
        ports = list_serial_ports()
        available_port_paths = [p.device for p in ports]
        
        if saved_port in available_port_paths:
            logger.info(f"Using saved port: {saved_port}")
            return saved_port
        else:
            logger.warning(f"Saved port '{saved_port}' not found in available ports.")
            logger.info("Please select a new port:\n")
    
    # List available ports
    ports = list_serial_ports()
    
    if not ports:
        logger.warning("No serial ports found.")
        if saved_port:
            logger.info(f"Trying saved port: {saved_port}")
            return saved_port
        logger.error("Cannot continue without a port. Please connect a device and try again.")
        sys.exit(1)
    
    logger.info("Available serial ports:")
    logger.info("-" * 60)
    for i, port in enumerate(ports, 1):
        description = port.description or "N/A"
        hwid = f" [{port.hwid}]" if port.hwid else ""
        marker = " ← saved" if saved_port and port.device == saved_port else ""
        logger.info(f"  {i}. {port.device} - {description}{hwid}{marker}")
    logger.info(f"  {len(ports) + 1}. Enter custom port path")
    logger.info("-" * 60)
    
    while True:
        try:
            default_hint = f" [{saved_port}]" if saved_port else ""
            choice = input(f"\nSelect port (1-{len(ports) + 1}) or press Enter{default_hint}: ").strip()
            
            if not choice:
                if saved_port:
                    return saved_port
                logger.warning("No port selected. Please choose a port.")
                continue
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(ports):
                selected = ports[choice_num - 1].device
                save_port(selected)  # Save for next time
                return selected
            elif choice_num == len(ports) + 1:
                custom = input("Enter port path: ").strip()
                if custom:
                    save_port(custom)  # Save for next time
                    return custom
                logger.warning("Invalid port path. Please try again.")
            else:
                logger.warning(f"Invalid choice. Please enter a number between 1 and {len(ports) + 1}.")
        except ValueError:
            logger.warning("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            logger.info("\nCancelled.")
            sys.exit(0)

async def main():
    # Select port (interactive or from command line)
    port = select_port()
    
    # Parse channel index from command line arguments
    channel_idx = CHANNEL_IDX
    # If first arg was a port, channel is second arg; otherwise first arg might be channel
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # If first arg is not a port path, it might be a channel number
        if not (first_arg.startswith('/dev/') or first_arg.startswith('COM') or ':' in first_arg):
            try:
                channel_idx = int(first_arg)
            except ValueError:
                pass  # Ignore if not a number
        # Check for second argument (channel)
        if len(sys.argv) > 2:
            try:
                channel_idx = int(sys.argv[2])
            except ValueError:
                print(f"Warning: Invalid channel index '{sys.argv[2]}'. Using default channel {CHANNEL_IDX}")
    
    logger.info("")
    logger.info("Alert Bot Starting...")
    logger.info(f"  Port: {port}")
    logger.info(f"  Channel: {channel_idx}")
    logger.info(f"  Messages per cycle: {len(MESSAGES)}")
    logger.info(f"  Interval between messages: {MESSAGE_INTERVAL_SECONDS} seconds")
    logger.info(f"  Cycle interval: {CYCLE_INTERVAL_MINUTES} minutes")
    logger.info(f"  Press Ctrl+C to stop")
    logger.info("")
    
    try:
        # Connect to device with auto-reconnect enabled
        logger.info(f"Connecting to {port}...")
        try:
            mc = await MeshCore.create_serial(port, BAUDRATE, debug=False, auto_reconnect=True, max_reconnect_attempts=5)
            logger.info("✓ Connected successfully!")
            logger.info("")
        except Exception as e:
            logger.error(f"✗ Failed to connect to {port}: {e}")
            logger.info("")
            logger.info("Port may not be available. Please select a different port:")
            logger.info("")
            # Try selecting a new port (skip saved port since it just failed)
            port = select_port(skip_saved=True)
            logger.info("")
            logger.info(f"Retrying connection to {port}...")
            mc = await MeshCore.create_serial(port, BAUDRATE, debug=False, auto_reconnect=True, max_reconnect_attempts=5)
            logger.info("✓ Connected successfully!")
            logger.info("")
        
        # Track connection state ourselves (more reliable than is_connected property)
        connection_state = {'connected': True}  # Use dict to allow modification in nested functions
        
        # Monitor connection status (permanent background monitoring)
        async def on_connected(event):
            nonlocal connection_state
            timestamp = datetime.now().strftime("%H:%M:%S")
            connection_state['connected'] = True
            if event.payload.get('reconnected'):
                logger.info("")
                logger.info(f"[{timestamp}] ✓ Connection restored!")
            else:
                logger.info(f"[{timestamp}] ✓ Connected")
        
        async def on_disconnected(event):
            nonlocal connection_state
            timestamp = datetime.now().strftime("%H:%M:%S")
            reason = event.payload.get('reason', 'unknown')
            connection_state['connected'] = False
            logger.warning("")
            logger.warning(f"[{timestamp}] ⚠ Connection lost: {reason}")
            logger.info(f"[{timestamp}] Monitoring for reconnection...")
        
        # Subscribe to connection events (permanent monitoring)
        mc.subscribe(EventType.CONNECTED, on_connected)
        mc.subscribe(EventType.DISCONNECTED, on_disconnected)
        
        # Get device info
        result = await mc.commands.send_appstart()
        if result.type != EventType.ERROR:
            device_name = result.payload.get('name') or result.payload.get('adv_name', 'Unknown')
            logger.info(f"Device: {device_name}")
            logger.info("")
        
        # Verify channel exists (optional check)
        logger.info(f"Checking channel {channel_idx}...")
        result = await mc.commands.get_channel(channel_idx)
        if result.type == EventType.CHANNEL_INFO:
            channel_name = result.payload.get('channel_name', 'Unnamed')
            logger.info(f"✓ Channel {channel_idx}: '{channel_name}'")
            logger.info("")
        elif result.type == EventType.ERROR:
            logger.warning(f"⚠ Warning: Could not get channel info: {result.payload}")
            logger.info(f"  Continuing anyway (channel might be public/unconfigured)")
            logger.info("")
        
        # Background task to periodically check and reconnect if needed
        async def periodic_reconnect_check():
            """Periodically check if device is available and reconnect if needed"""
            nonlocal port
            while True:
                await asyncio.sleep(5)  # Check every 5 seconds
                if not connection_state['connected']:
                    # Try to reconnect if port is available
                    if os.path.exists(port):
                        try:
                            # Try to reconnect through the connection manager
                            if hasattr(mc.connection_manager, 'connection'):
                                # Update port on connection object if it changed
                                if hasattr(mc.connection_manager.connection, 'port'):
                                    if mc.connection_manager.connection.port != port:
                                        mc.connection_manager.connection.port = port
                                
                                try:
                                    result = await mc.connection_manager.connection.connect()
                                    if result is not None:
                                        # Connection successful, update state
                                        connection_state['connected'] = True
                                        timestamp = datetime.now().strftime("%H:%M:%S")
                                        logger.info("")
                                        logger.info(f"[{timestamp}] ✓ Reconnection successful!")
                                except Exception:
                                    pass  # Continue checking
                        except Exception:
                            pass  # Continue checking
        
        # Start background reconnection checker
        reconnect_checker_task = asyncio.create_task(periodic_reconnect_check())
        
        # Start sending messages
        total_messages_sent = 0
        cycle_count = 0
        logger.info("Starting message cycles...")
        logger.info("=" * 60)
        
        try:
            while True:
                cycle_count += 1
                cycle_start_time = datetime.now().timestamp()
                cycle_start = datetime.fromtimestamp(cycle_start_time).strftime("%H:%M:%S")
                logger.info("")
                logger.info(f"[Cycle {cycle_count}] Starting at {cycle_start}")
                logger.info("-" * 60)
                
                # Send all messages in the cycle with intervals
                for i, message in enumerate(MESSAGES, 1):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    status_msg = f"[{timestamp}] Sending message {i}/{len(MESSAGES)}..."
                    
                    # Check connection state - if not connected, skip message and continue
                    if not connection_state['connected']:
                        logger.warning(f"{status_msg} ⚠ Skipped (device not connected)")
                        if i < len(MESSAGES):
                            await asyncio.sleep(MESSAGE_INTERVAL_SECONDS)
                        continue
                    
                    # Try sending message
                    result = await mc.commands.send_chan_msg(channel_idx, message)
                    
                    if result.type == EventType.ERROR:
                        error_reason = result.payload.get('reason', '')
                        # If connection lost or no response, update state and skip
                        if error_reason == 'no_event_received' or not connection_state['connected']:
                            logger.warning(f"{status_msg} ⚠ Skipped (connection issue)")
                            # Update state in case it changed during send
                            connection_state['connected'] = mc.is_connected
                        else:
                            logger.error(f"{status_msg} ✗ Error: {result.payload}")
                    else:
                        total_messages_sent += 1
                        logger.info(f"{status_msg} ✓ Sent")
                    
                    # Wait before next message (except after last message)
                    if i < len(MESSAGES):
                        await asyncio.sleep(MESSAGE_INTERVAL_SECONDS)
                
                # Calculate wait time to start next cycle at exact interval
                # Next cycle should start at: cycle_start_time + CYCLE_INTERVAL_MINUTES
                next_cycle_time = cycle_start_time + (CYCLE_INTERVAL_MINUTES * 60)
                # Wait time = next cycle time - current time
                current_time = datetime.now().timestamp()
                wait_seconds = next_cycle_time - current_time
                
                next_cycle_str = datetime.fromtimestamp(next_cycle_time).strftime("%H:%M:%S")
                wait_minutes = int(wait_seconds / 60)
                wait_secs = int(wait_seconds % 60)
                logger.info("")
                logger.info(f"✓ Cycle {cycle_count} complete. Next cycle at {next_cycle_str}")
                logger.info(f"  (Waiting {wait_minutes}m {wait_secs}s... Total messages sent: {total_messages_sent})")
                logger.info("=" * 60)
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Stopping bot...")
            logger.info(f"Total cycles completed: {cycle_count}")
            logger.info(f"Total messages sent: {total_messages_sent}")
            # Cancel background tasks
            if reconnect_checker_task:
                reconnect_checker_task.cancel()
                try:
                    await reconnect_checker_task
                except asyncio.CancelledError:
                    pass
        
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'mc' in locals():
            await mc.disconnect()
            logger.info("✓ Disconnected")

if __name__ == "__main__":
    asyncio.run(main())

