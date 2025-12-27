#!/usr/bin/env python3
"""
Check and synchronize MeshCore device clock with system time
Usage: python time_sync.py [--sync]
"""

import asyncio
import sys
import time
from datetime import datetime
from meshcore import MeshCore, EventType

PORT = "/dev/tty.usbmodem90706983D6801"
BAUDRATE = 115200
MAX_TIME_DIFF_SECONDS = 5  # Consider synced if within 5 seconds

async def main():
    sync_requested = "--sync" in sys.argv or "-s" in sys.argv
    
    print("Clock Synchronization Check")
    print("=" * 60)
    
    try:
        # Connect to device
        print(f"Connecting to {PORT}...")
        mc = await MeshCore.create_serial(PORT, BAUDRATE, debug=False)
        print("✓ Connected successfully!\n")
        
        # Get system time
        system_time = int(time.time())
        system_datetime = datetime.fromtimestamp(system_time)
        print(f"System Time:")
        print(f"  Unix timestamp: {system_time}")
        print(f"  Human readable: {system_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get device time
        print(f"\nGetting device time...")
        result = await mc.commands.get_time()
        
        if result.type == EventType.ERROR:
            print(f"✗ Error getting device time: {result.payload}")
            await mc.disconnect()
            return
        
        if result.type != EventType.CURRENT_TIME:
            print(f"✗ Unexpected response type: {result.type}")
            await mc.disconnect()
            return
        
        device_time = result.payload
        if isinstance(device_time, dict):
            device_timestamp = device_time.get('time', None)
        else:
            device_timestamp = device_time
        
        if device_timestamp is None:
            print(f"✗ Could not extract timestamp from response: {result.payload}")
            await mc.disconnect()
            return
        
        device_datetime = datetime.fromtimestamp(device_timestamp)
        
        print(f"\nDevice Time:")
        print(f"  Unix timestamp: {device_timestamp}")
        print(f"  Human readable: {device_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate difference
        time_diff = abs(system_time - device_timestamp)
        time_diff_seconds = time_diff
        time_diff_minutes = time_diff_seconds / 60
        time_diff_hours = time_diff_minutes / 60
        
        print(f"\nTime Difference:")
        print(f"  Absolute difference: {time_diff_seconds} seconds")
        if time_diff_seconds >= 60:
            print(f"  ({time_diff_minutes:.1f} minutes)")
        if time_diff_seconds >= 3600:
            print(f"  ({time_diff_hours:.2f} hours)")
        
        # Check if synced
        is_synced = time_diff_seconds <= MAX_TIME_DIFF_SECONDS
        
        if is_synced:
            print(f"\n✓ Clocks are synced! (within {MAX_TIME_DIFF_SECONDS} seconds)")
        else:
            print(f"\n⚠ Clocks are NOT synced! (difference: {time_diff_seconds} seconds)")
            
            if sync_requested:
                print(f"\nSyncing device time to system time...")
                result = await mc.commands.set_time(system_time)
                
                if result.type == EventType.ERROR:
                    print(f"✗ Error syncing time: {result.payload}")
                else:
                    print(f"✓ Device time synced successfully!")
                    
                    # Verify sync
                    print(f"\nVerifying sync...")
                    await asyncio.sleep(0.5)  # Small delay
                    result = await mc.commands.get_time()
                    
                    if result.type == EventType.CURRENT_TIME:
                        new_device_time = result.payload
                        if isinstance(new_device_time, dict):
                            new_timestamp = new_device_time.get('time', None)
                        else:
                            new_timestamp = new_device_time
                        
                        if new_timestamp:
                            new_diff = abs(system_time - new_timestamp)
                            print(f"  New difference: {new_diff} seconds")
                            if new_diff <= MAX_TIME_DIFF_SECONDS:
                                print(f"✓ Sync verified!")
                            else:
                                print(f"⚠ Sync may not have taken effect yet")
            else:
                print(f"\nTo sync the device time, run with --sync flag:")
                print(f"  python time_sync.py --sync")
        
        await mc.disconnect()
        print(f"\n✓ Disconnected")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

