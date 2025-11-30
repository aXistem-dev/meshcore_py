#!/usr/bin/env python3
"""
MeshCore Serial-to-TCP Bridge

This script bridges a MeshCore device connected via serial (USB) to TCP,
allowing remote clients to connect to the device over the network.

Usage:
    python serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000

On Raspberry Pi with Heltec V3:
    python serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000 --baud 115200
"""

import asyncio
import argparse
import logging
import sys
from typing import Optional

# Frame format: 0x3C + 2 bytes (little endian size) + payload
FRAME_START = b"\x3c"


class SerialToTCPBridge:
    """Bridges MeshCore serial connection to TCP server"""
    
    def __init__(self, serial_port: str, baudrate: int = 115200, tcp_port: int = 5000, tcp_host: str = "0.0.0.0"):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.tcp_port = tcp_port
        self.tcp_host = tcp_host
        
        self.serial_transport = None
        self.tcp_clients = set()
        
        # Frame parsing state for serial
        self.serial_frame_started = False
        self.serial_frame_size = 0
        self.serial_header = b""
        self.serial_inframe = b""
        
        self.logger = logging.getLogger("serial_to_tcp_bridge")
        
    class SerialProtocol(asyncio.Protocol):
        """Protocol handler for serial connection"""
        def __init__(self, bridge):
            self.bridge = bridge
            self.transport = None
        
        def connection_made(self, transport):
            self.transport = transport
            self.bridge.serial_transport = transport
            self.bridge.logger.info(f"Connected to serial port: {self.bridge.serial_port} at {self.bridge.baudrate} baud")
        
        def data_received(self, data):
            asyncio.create_task(self.bridge.parse_serial_frames(data))
        
        def connection_lost(self, exc):
            self.bridge.logger.warning("Serial port closed")
            self.bridge.serial_transport = None
        
    async def connect_serial(self):
        """Connect to serial port"""
        try:
            import serial_asyncio
            loop = asyncio.get_running_loop()
            await serial_asyncio.create_serial_connection(
                loop,
                lambda: self.SerialProtocol(self),
                self.serial_port,
                baudrate=self.baudrate,
            )
        except ImportError:
            self.logger.error("pyserial-asyncio not installed. Install with: pip install pyserial-asyncio")
            raise
        except Exception as e:
            self.logger.error(f"Failed to connect to serial port: {e}")
            raise
    
    async def handle_serial_frame(self, frame: bytes):
        """Forward a complete frame from serial to all TCP clients"""
        if not self.tcp_clients:
            return
        
        # Frame format: 0x3C + 2 bytes size + payload
        size = len(frame)
        packet = FRAME_START + size.to_bytes(2, byteorder="little") + frame
        
        # Send to all connected TCP clients
        disconnected_clients = []
        for client_writer in self.tcp_clients:
            try:
                client_writer.write(packet)
                await client_writer.drain()
            except Exception as e:
                self.logger.warning(f"Error sending to TCP client: {e}")
                disconnected_clients.append(client_writer)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.tcp_clients.discard(client)
            try:
                client.close()
                await client.wait_closed()
            except:
                pass
    
    async def parse_serial_frames(self, data: bytes):
        """Parse MeshCore frames from serial data"""
        i = 0
        while i < len(data):
            if not self.serial_frame_started:
                # Look for frame start
                if data[i] == FRAME_START[0]:
                    # Found start, need at least 3 bytes for header
                    if len(data) - i >= 3:
                        self.serial_header = data[i:i+3]
                        self.serial_frame_size = int.from_bytes(self.serial_header[1:3], byteorder="little")
                        self.serial_frame_started = True
                        i += 3
                    else:
                        # Not enough data, save what we have
                        self.serial_header = data[i:]
                        break
                else:
                    i += 1
            else:
                # Reading frame payload
                remaining = self.serial_frame_size - len(self.serial_inframe)
                if len(data) - i >= remaining:
                    self.serial_inframe += data[i:i+remaining]
                    # Complete frame received
                    await self.handle_serial_frame(self.serial_inframe)
                    # Reset state
                    self.serial_frame_started = False
                    self.serial_header = b""
                    self.serial_inframe = b""
                    i += remaining
                else:
                    # Not enough data, save what we have
                    self.serial_inframe += data[i:]
                    break
    
    async def handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new TCP client connection"""
        client_addr = writer.get_extra_info('peername')
        self.logger.info(f"TCP client connected: {client_addr}")
        self.tcp_clients.add(writer)
        
        # Frame parsing state for this TCP client
        frame_started = False
        frame_size = 0
        header = b""
        inframe = b""
        
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                # Parse frames from TCP data
                i = 0
                while i < len(data):
                    if not frame_started:
                        # Look for frame start
                        if data[i] == FRAME_START[0]:
                            # Found start, need at least 3 bytes for header
                            if len(data) - i >= 3:
                                header = data[i:i+3]
                                frame_size = int.from_bytes(header[1:3], byteorder="little")
                                frame_started = True
                                i += 3
                            else:
                                # Not enough data, save what we have
                                header = data[i:]
                                break
                        else:
                            i += 1
                    else:
                        # Reading frame payload
                        remaining = frame_size - len(inframe)
                        if len(data) - i >= remaining:
                            inframe += data[i:i+remaining]
                            # Complete frame received, forward to serial (header + payload)
                            if self.serial_transport:
                                try:
                                    full_frame = header + inframe
                                    self.serial_transport.write(full_frame)
                                except Exception as e:
                                    self.logger.error(f"Error writing to serial: {e}")
                                    break
                            # Reset state
                            frame_started = False
                            header = b""
                            inframe = b""
                            i += remaining
                        else:
                            # Not enough data, save what we have
                            inframe += data[i:]
                            break
                            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error handling TCP client {client_addr}: {e}")
        finally:
            self.logger.info(f"TCP client disconnected: {client_addr}")
            self.tcp_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    async def start_tcp_server(self):
        """Start TCP server"""
        server = await asyncio.start_server(
            self.handle_tcp_client,
            self.tcp_host,
            self.tcp_port
        )
        addr = server.sockets[0].getsockname()
        self.logger.info(f"TCP server listening on {addr[0]}:{addr[1]}")
        return server
    
    async def run(self):
        """Run the bridge"""
        # Connect to serial
        await self.connect_serial()
        
        # Start TCP server
        server = await self.start_tcp_server()
        
        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            # Close all TCP clients
            for client in list(self.tcp_clients):
                try:
                    client.close()
                    await client.wait_closed()
                except:
                    pass
            
            # Close serial connection
            if self.serial_transport:
                self.serial_transport.close()
            
            self.logger.info("Bridge stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Bridge MeshCore serial connection to TCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bridge /dev/ttyUSB0 to TCP port 5000
  python serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000
  
  # Use custom baudrate and bind to specific interface
  python serial_to_tcp_bridge.py --serial /dev/ttyUSB0 --port 5000 --baud 115200 --host 0.0.0.0
        """
    )
    parser.add_argument(
        "-s", "--serial",
        required=True,
        help="Serial port path (e.g., /dev/ttyUSB0)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=5000,
        help="TCP port to listen on (default: 5000)"
    )
    parser.add_argument(
        "-b", "--baud",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="TCP host to bind to (default: 0.0.0.0 for all interfaces)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run bridge
    bridge = SerialToTCPBridge(
        serial_port=args.serial,
        baudrate=args.baud,
        tcp_port=args.port,
        tcp_host=args.host
    )
    
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()

