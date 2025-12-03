#!/usr/bin/env python3
"""
Serial to TCP Bridge for MeshCore devices

This script bridges a serial USB MeshCore device to TCP, allowing remote access
via TCP connections. Multiple TCP clients can connect simultaneously.

Usage:
    python serial_to_tcp_bridge.py [--serial-port PORT] [--baudrate RATE] [--tcp-host HOST] [--tcp-port PORT] [--debug]

Example:
    python serial_to_tcp_bridge.py --serial-port /dev/ttyUSB0 --tcp-port 5000
"""

import asyncio
import argparse
import logging
import serial_asyncio
from typing import Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("serial_tcp_bridge")


class SerialToTCPBridge:
    def __init__(self, serial_port: str, baudrate: int = 115200, tcp_host: str = "0.0.0.0", tcp_port: int = 5000):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.serial_transport = None
        self.serial_protocol = None
        self.tcp_clients: Set[asyncio.StreamWriter] = set()
        self.running = True

    class SerialProtocol(asyncio.Protocol):
        def __init__(self, bridge):
            self.bridge = bridge
            self.buffer = b""

        def connection_made(self, transport):
            self.bridge.serial_transport = transport
            logger.info(f"Serial connection established on {self.bridge.serial_port}")
            if isinstance(transport, serial_asyncio.SerialTransport) and transport.serial:
                transport.serial.rts = False

        def data_received(self, data):
            # Forward serial data to all TCP clients
            if self.bridge.tcp_clients:
                # Create a copy of the set to avoid modification during iteration
                clients_to_remove = set()
                for writer in self.bridge.tcp_clients.copy():
                    try:
                        if not writer.is_closing():
                            writer.write(data)
                            # Schedule drain asynchronously
                            asyncio.create_task(self._drain_writer(writer))
                    except Exception as e:
                        logger.error(f"Error writing to TCP client: {e}")
                        clients_to_remove.add(writer)
                
                # Remove dead clients
                for writer in clients_to_remove:
                    self.bridge.tcp_clients.discard(writer)
                    try:
                        writer.close()
                    except:
                        pass

        async def _drain_writer(self, writer):
            """Drain a single writer"""
            try:
                if not writer.is_closing():
                    await writer.drain()
            except Exception as e:
                logger.debug(f"Error draining writer: {e}")

        def connection_lost(self, exc):
            logger.warning(f"Serial connection lost: {exc}")
            self.bridge.running = False

    async def handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new TCP client connection"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"TCP client connected: {client_addr}")
        self.tcp_clients.add(writer)

        try:
            while self.running:
                data = await reader.read(4096)
                if not data:
                    break
                
                # Forward TCP data to serial
                if self.serial_transport and not self.serial_transport.is_closing():
                    self.serial_transport.write(data)
                else:
                    logger.warning("Serial transport not available, dropping TCP data")
                    break
        except Exception as e:
            logger.error(f"Error handling TCP client {client_addr}: {e}")
        finally:
            logger.info(f"TCP client disconnected: {client_addr}")
            self.tcp_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    async def start_serial(self):
        """Start serial connection"""
        loop = asyncio.get_running_loop()
        self.serial_protocol = self.SerialProtocol(self)
        _, self.serial_protocol = await serial_asyncio.create_serial_connection(
            loop,
            lambda: self.serial_protocol,
            self.serial_port,
            baudrate=self.baudrate,
        )
        logger.info(f"Serial connection started on {self.serial_port} at {self.baudrate} baud")

    async def start_tcp_server(self):
        """Start TCP server"""
        server = await asyncio.start_server(
            self.handle_tcp_client,
            self.tcp_host,
            self.tcp_port
        )
        addr = server.sockets[0].getsockname()
        logger.info(f"TCP server started on {addr[0]}:{addr[1]}")
        logger.info(f"Connect to this bridge using: meshcli -t {addr[0]} -p {addr[1]} <command>")
        
        async with server:
            await server.serve_forever()

    async def run(self):
        """Run the bridge"""
        try:
            # Start serial connection
            await self.start_serial()
            
            # Start TCP server
            await self.start_tcp_server()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error in bridge: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.serial_transport:
            self.serial_transport.close()
        for writer in self.tcp_clients:
            try:
                writer.close()
            except:
                pass
        logger.info("Bridge stopped")


async def main():
    parser = argparse.ArgumentParser(description="Serial to TCP Bridge for MeshCore devices")
    parser.add_argument("--serial-port", "-s", default="/dev/ttyUSB0", help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baudrate", "-b", type=int, default=115200, help="Serial baudrate (default: 115200)")
    parser.add_argument("--tcp-host", default="0.0.0.0", help="TCP server host (default: 0.0.0.0)")
    parser.add_argument("--tcp-port", "-p", type=int, default=5000, help="TCP server port (default: 5000)")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    bridge = SerialToTCPBridge(
        serial_port=args.serial_port,
        baudrate=args.baudrate,
        tcp_host=args.tcp_host,
        tcp_port=args.tcp_port
    )
    
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())

