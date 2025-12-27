#!/usr/bin/env python3
"""
Display MeshCore device information (model, firmware, battery, storage, etc.)
Usage: python device_info.py [port]
"""

import asyncio
import sys
from serial.tools import list_ports
from meshcore import MeshCore, EventType

DEFAULT_PORT = "/dev/tty.usbmodem90706983D6801"
BAUDRATE = 115200

def list_serial_ports():
    """List all available serial ports, preferring tty over cu on macOS"""
    ports = list_ports.comports()
    if not ports:
        return []
    
    # On macOS, prefer tty over cu versions
    if sys.platform == 'darwin':
        port_dict = {}
        for port in ports:
            port_str = port.device
            if port_str.startswith('/dev/tty.'):
                # Use tty version
                base_name = port_str.replace('/dev/tty.', '')
                port_dict[base_name] = port
            elif port_str.startswith('/dev/cu.'):
                # Only use cu if no tty version exists
                base_name = port_str.replace('/dev/cu.', '')
                if base_name not in port_dict:
                    port_dict[base_name] = port
        return list(port_dict.values())
    
    return ports

def select_port():
    """Interactively select a serial port"""
    # Check if port provided as argument
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # List available ports
    ports = list_serial_ports()
    
    if not ports:
        print("No serial ports found. Using default port.")
        return DEFAULT_PORT
    
    print("Available serial ports:")
    print("-" * 60)
    for i, port in enumerate(ports, 1):
        description = port.description or "N/A"
        hwid = f" [{port.hwid}]" if port.hwid else ""
        print(f"  {i}. {port.device} - {description}{hwid}")
    print(f"  {len(ports) + 1}. Enter custom port path")
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"\nSelect port (1-{len(ports) + 1}) or press Enter for default [{DEFAULT_PORT}]: ").strip()
            
            if not choice:
                return DEFAULT_PORT
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(ports):
                return ports[choice_num - 1].device
            elif choice_num == len(ports) + 1:
                custom = input("Enter port path: ").strip()
                if custom:
                    return custom
                print("Invalid port path. Please try again.")
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(ports) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

async def main():
    port = select_port()
    print(f"\nConnecting to {port} at {BAUDRATE} baud...")
    
    try:
        mc = await MeshCore.create_serial(port, BAUDRATE, debug=False)
        print("✓ Connected successfully!\n")
        
        # Get device info
        print("Getting device information...")
        result = await mc.commands.send_device_query()
        if result.type == EventType.ERROR:
            print(f"✗ Error: {result.payload}")
        else:
            info = result.payload
            print(f"  Model: {info.get('model', 'N/A')}")
            # Try different firmware version field names
            firmware = info.get('ver') or info.get('fw ver') or info.get('fw_build') or 'N/A'
            print(f"  Firmware: {firmware}")
            print(f"  Max Contacts: {info.get('max_contacts', 'N/A')}")
            print(f"  Max Channels: {info.get('max_channels', 'N/A')}")
        
        # Get self info
        print("\nGetting self information...")
        result = await mc.commands.send_appstart()
        if result.type == EventType.ERROR:
            print(f"✗ Error: {result.payload}")
        else:
            self_info = result.payload
            # Try both 'name' and 'adv_name' field names
            name = self_info.get('name') or self_info.get('adv_name') or 'N/A'
            print(f"  Name: {name}")
            print(f"  Public Key: {self_info.get('public_key', 'N/A')[:24]}...")
            # Check for coordinates in both formats
            lat = self_info.get('lat') or self_info.get('adv_lat')
            lon = self_info.get('lon') or self_info.get('adv_lon')
            if lat is not None and lon is not None:
                print(f"  Coordinates: {lat}, {lon}")
        
        # Get battery
        print("\nGetting battery status...")
        result = await mc.commands.get_bat()
        if result.type == EventType.ERROR:
            print(f"✗ Error: {result.payload}")
        else:
            bat = result.payload
            battery_mv = bat.get('level')
            if battery_mv is not None:
                # Battery is in millivolts, convert to volts and optionally to percentage
                battery_v = battery_mv / 1000.0
                # Typical LiPo range: 3.0V (empty) to 4.2V (full)
                # Calculate approximate percentage
                min_voltage = 3.0
                max_voltage = 4.2
                if battery_v >= max_voltage:
                    battery_percent = 100
                elif battery_v <= min_voltage:
                    battery_percent = 0
                else:
                    battery_percent = int(((battery_v - min_voltage) / (max_voltage - min_voltage)) * 100)
                print(f"  Battery: {battery_v:.2f}V ({battery_mv}mV) ~{battery_percent}%")
            else:
                print(f"  Battery Level: N/A")
            # Storage is in kilobytes
            used_kb = bat.get('used_kb')
            total_kb = bat.get('total_kb')
            if used_kb is not None and total_kb is not None:
                # Display in KB, MB, or bytes as appropriate
                if total_kb >= 1024:
                    used_mb = used_kb / 1024
                    total_mb = total_kb / 1024
                    print(f"  Storage: {used_mb:.2f}/{total_mb:.2f} MB ({used_kb}/{total_kb} KB)")
                else:
                    used_bytes = used_kb * 1024
                    total_bytes = total_kb * 1024
                    print(f"  Storage: {used_bytes}/{total_bytes} bytes ({used_kb}/{total_kb} KB)")
            else:
                print(f"  Storage: N/A (not available)")
        
        await mc.disconnect()
        print("\n✓ Disconnected successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

