"""
Module: Reverse Proxy with Logging
Author: Anubhav Patrick
Date: 2025-03-18
Time: 12:34 PM

Brief Summary:
This module implements a reverse proxy server using Python's `aiohttp` library. 
The server accepts requests from local clients, forwards those requests to a remote server (using the 
public IP and port), and returns the response to the client. The module includes logging capabilities 
that capture errors, warnings, and critical issues, while suppressing info-level logs to prevent log b
loat. A rotating log handler is used to ensure that logs do not become too large.

Key Features:
- Maps private IP/port of local clients to the public IP/port of remote services.
- Forwards client requests to the remote service and returns the response.
- Logs only warnings, errors, and critical issues (logs info-level messages are suppressed).
- Utilizes rotating logs to limit log file size and manage backups (max 10MB per log file, up to 5 backups).
- Handles errors gracefully, including failed forwarding and network issues.

Dependencies:
- aiohttp: For handling asynchronous HTTP requests and server functionality.
- logging: For logging error, warning, and critical information, with a rotating log handler.

"""

import logging
from logging.handlers import RotatingFileHandler
from aiohttp import web
import aiohttp
import json
import pytz
from datetime import datetime

# Define a custom log formatter to use IST time zone
class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Get the UTC time and convert to IST (UTC+5:30)
        utc_time = datetime.utcfromtimestamp(record.created)
        ist_time = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Kolkata'))
        
        # Format the time as per your requirements
        return ist_time.strftime('%Y-%m-%d %H:%M:%S')

    def format(self, record):
        # Add the custom formatted time
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Now let the default formatter do the rest (formatting levelname and message)
        return super().format(record)

# Load the configuration from the config.json file
def load_config(config_path='config.json'):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_path}' not found.")
        raise # It will raise 
    except json.JSONDecodeError:
        logger.error(f"Configuration file '{config_path}' is not valid JSON.")
        raise

# Load configuration
config = load_config()

# Set up the logger with rotating log files
log_formatter = ISTFormatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(config["log_file_path"], maxBytes=config["log_max_size"], backupCount=config["log_backup_count"])
log_handler.setFormatter(log_formatter)

logger = logging.getLogger('ProxyLogger')

# Set log level dynamically based on config
log_level = getattr(logging, config["log_level"].upper(), logging.WARNING)
logger.setLevel(log_level)
logger.addHandler(log_handler)


# Reverse proxy mapping from config
reverse_proxy_map = {}
local_ip = None
local_port = None
for key, value in config["reverse_proxy_map"].items():
    local_ip, local_port = key.split(':')
    reverse_proxy_map[(local_ip, int(local_port))] = (value["remote_ip"], value["remote_port"])

async def proxy_handler(request):
    private_ip = request.host.split(':')[0]
    private_port = request.url.port
    client_ip = request.remote

    remote_ip, remote_port = reverse_proxy_map.get((private_ip, private_port), (None, None))

    if not remote_ip or not remote_port:
        logger.warning(f"Client {client_ip} made a request for {private_ip}:{private_port}{request.rel_url}. "
                       "No mapping found.")
        return web.Response(status=404, text="No mapping found for this IP and port")

    remote_url = f'http://{remote_ip}:{remote_port}{request.rel_url}'
    
    # Check if this is a WebSocket request
    is_websocket = request.headers.get('Upgrade', '').lower() == 'websocket'
    
    if is_websocket:
        # Handle WebSocket connections
        try:
            # Create a WebSocket connection to the remote server
            ws_client = web.WebSocketResponse()
            await ws_client.prepare(request)
            
            # Connect to the remote WebSocket server
            async with aiohttp.ClientSession() as session:
                # Prepare headers for the WebSocket connection
                ws_headers = {k: v for k, v in request.headers.items() 
                             if k.lower() not in ('host', 'origin')}
                
                # Adjust the origin header to match the remote server
                ws_headers['Origin'] = f'http://{remote_ip}:{remote_port}'
                
                async with session.ws_connect(
                    remote_url, 
                    headers=ws_headers,
                    protocols=request.headers.get('Sec-WebSocket-Protocol', '').split(',')
                ) as ws_server:
                    # Create bidirectional communication
                    async def forward_ws_messages(source, destination):
                        async for msg in source:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await destination.send_str(msg.data)
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await destination.send_bytes(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                    
                    # Create tasks for bidirectional communication
                    import asyncio
                    client_to_server = asyncio.create_task(forward_ws_messages(ws_client, ws_server))
                    server_to_client = asyncio.create_task(forward_ws_messages(ws_server, ws_client))
                    
                    # Wait for either connection to close
                    try:
                        await asyncio.gather(client_to_server, server_to_client)
                    except asyncio.CancelledError:
                        client_to_server.cancel()
                        server_to_client.cancel()
            
            return ws_client
                
        except Exception as e:
            logger.error(f"Error handling WebSocket for {remote_url}: {str(e)}")
            return web.Response(status=500, text="Error establishing WebSocket connection")
    
    # Handle regular HTTP requests (your existing code)
    try:
        data = await request.read() if request.body_exists else None
        headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method, 
                remote_url, 
                headers=headers,
                data=data,
                allow_redirects=False
            ) as response:
                content = await response.read()
                
                client_response = web.Response(
                    status=response.status,
                    body=content
                )
                
                for header, value in response.headers.items():
                    if header.lower() != 'transfer-encoding':
                        client_response.headers[header] = value
                
                if response.status >= 400:
                    logger.warning(f"Client {client_ip} made a request for {remote_url}. "
                                   f"Received status: {response.status}.")
                
                return client_response

    except Exception as e:
        logger.error(f"Error forwarding request from client {client_ip} for {request.rel_url} to remote IP {remote_ip}: {str(e)}")
        return web.Response(status=500, text="Error forwarding request. Please try again later.")

# Main application setup
app = web.Application()
app.router.add_route('*', '/{path:.*}', proxy_handler)  # Catch all routes and forward them

def run_app():
    """
    Starts the proxy server and runs the application. The server listens on the local host 
    (`0.0.0.0`) and port 31388, handling incoming requests from local clients and forwarding them 
    to the corresponding remote services.
    
    The server logs the startup process as an info-level message (suppressed in this case due to the 
    logging level set to WARNING).
    """
    logger.info("Starting the proxy server...")  # This line is now suppressed because the log level is set to WARNING
    web.run_app(app, host=config["server"]["host"], port=int(local_port))  # The local server that listens to local clients

# Run the application
if __name__ == '__main__':
    run_app()
