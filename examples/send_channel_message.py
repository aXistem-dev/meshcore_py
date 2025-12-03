#!/usr/bin/python
"""
Example of sending a message to a channel

Usage:
    python send_channel_message.py -p /dev/ttyUSB0 --channel "#test" --message "Test"
    python send_channel_message.py -p /dev/ttyUSB0 --channel-index 0 --message "Test"
"""

import asyncio
import argparse
from meshcore import MeshCore, EventType

async def find_channel_by_name(mc, channel_name):
    """Try to find a channel by name by checking common indices"""
    # Check channels 0-255
    for idx in range(256):
        result = await mc.commands.get_channel(idx)
        if result.type == EventType.CHANNEL_INFO:
            payload = result.payload
            if payload.get('channel_name', '').strip('\x00').strip() == channel_name:
                return idx
    return None

async def main():
    parser = argparse.ArgumentParser(description="Send a message to a channel")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("-b", "--baudrate", type=int, default=115200, help="Baud rate")
    parser.add_argument("--channel", help="Channel name (e.g., '#test')")
    parser.add_argument("--channel-index", type=int, help="Channel index (0-255)")
    parser.add_argument("-m", "--message", default="Test", help="Message to send")
    args = parser.parse_args()

    # Determine channel index
    channel_idx = None
    if args.channel_index is not None:
        channel_idx = args.channel_index
    elif args.channel:
        # Will need to find it after connecting
        channel_name = args.channel
    else:
        print("Error: Must specify either --channel or --channel-index")
        return

    # Connect to the device
    mc = await MeshCore.create_serial(args.port, args.baudrate, debug=False)

    try:
        # If channel name provided, try to find the channel index
        if args.channel and channel_idx is None:
            print(f"Searching for channel '{args.channel}'...")
            channel_idx = await find_channel_by_name(mc, args.channel)
            if channel_idx is None:
                print(f"Channel '{args.channel}' not found. Available options:")
                print("  - Use --channel-index to specify channel by number")
                print("  - Channel 0 is typically the public channel")
                print(f"  - Sending to channel 0 (public) instead...")
                channel_idx = 0
            else:
                print(f"Found channel '{args.channel}' at index {channel_idx}")
        elif channel_idx is None:
            channel_idx = 0  # Default to public channel

        # Send the channel message
        print(f"Sending message to channel {channel_idx}: '{args.message}'")
        result = await mc.commands.send_chan_msg(channel_idx, args.message)
        
        if result.type == EventType.ERROR:
            print(f"⚠️ Failed to send message: {result.payload}")
        elif result.type == EventType.OK:
            print(f"✅ Message sent successfully to channel {channel_idx}!")
        else:
            print(f"Response: {result.type} - {result.payload}")
    
    finally:
        await mc.disconnect()

if __name__ == "__main__":
    asyncio.run(main())


