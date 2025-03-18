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
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
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
    """
    Handles incoming HTTP requests from local clients, maps them to a remote public IP and port,
    forwards the request to the remote service, and returns the response back to the client.
    
    The function also logs errors, warnings, and critical issues based on the operation. 
    Only warning and error-level logs are recorded to reduce unnecessary logging verbosity.
    
    Args:
        request (aiohttp.web.Request): The incoming HTTP request from the local client.
        
    Returns:
        aiohttp.web.Response: The response to be sent back to the local client.
        If no mapping is found for the requested IP and port, a 404 response is returned.
        If an error occurs while forwarding the request, a 500 response is returned.
    
    Logs:
        - WARNING: Logged if no mapping for the private IP/port is found or if the response status 
                  from the remote server is a 4xx or 5xx error.
        - ERROR: Logged if there is an exception while forwarding the request to the remote server.
    """
    private_ip = request.host.split(':')[0]  # Extract the private IP
    private_port = request.url.port  # Get the port from the request URL
    client_ip = request.remote  # The IP address of the client making the request

    # Only log warnings, errors, and critical issues (info logging is now suppressed)
    remote_ip, remote_port = reverse_proxy_map.get((private_ip, private_port), (None, None))

    if not remote_ip or not remote_port:
        # Log the details of the error, but do not expose the remote IP to the client
        logger.warning(f"Client {client_ip} made a request for {private_ip}:{private_port}{request.rel_url}. "
                       "No mapping found.")  # Log as WARNING with client details
        return web.Response(status=404, text="No mapping found for this IP and port")

    # Construct the remote URL for the public application
    remote_url = f'http://{remote_ip}:{remote_port}{request.rel_url}'

    try:
        async with aiohttp.ClientSession() as session:
            # Forward the request to the remote application
            async with session.request(request.method, remote_url, headers=request.headers) as response:
                # Get the response from the remote service and forward it back to the local client
                data = await response.read()

                # Log the response status as a WARNING if needed
                if response.status >= 400:
                    # Log the remote IP for internal monitoring but don't expose it to the client
                    logger.warning(f"Client {client_ip} made a request for {remote_url}. "
                                   f"Received status: {response.status}.")  # Log warnings on 4xx/5xx errors

                return web.Response(status=response.status, body=data, headers=response.headers)

    except Exception as e:
        # Log the error with the remote IP for internal debugging
        logger.error(f"Error forwarding request from client {client_ip} for {request.rel_url} to remote IP {remote_ip}: {str(e)}")  # Log as ERROR with client details and remote IP
        # Return a generic error message to the client, without exposing the remote IP
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
    web.run_app(app, host=config["server"]["host"], port=local_port)  # The local server that listens to local clients

# Run the application
if __name__ == '__main__':
    run_app()