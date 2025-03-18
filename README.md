# Reverse Proxy with Logging

## Overview
This project implements a reverse proxy server using Python and the `aiohttp` library. The server listens for incoming HTTP requests from local clients, forwards them to a remote service (using a public IP and port), and returns the response back to the local client. It includes a logging mechanism that logs errors, warnings, and critical issues, with customizable log levels defined in the configuration file. The log files are stored in a local directory, which is mapped to the container when using Docker.

## Features
- **Proxying Requests**: Accepts incoming requests from local clients, forwards them to remote services, and returns the responses.
- **Configurable Logging**: Logs warnings, errors, and critical issues (configurable via log_level setting), including details like client IP and request URL.
- **Log Rotation**: The logs are stored in a file that rotates when it exceeds a configurable size (default 10MB), with a configurable number of backup files (default 5).
- **JSON Configuration**: All settings are stored in a `config.json` file for easy modification without code changes.
- **Dockerized**: The application is Dockerized, allowing for easy deployment and scaling.
- **Automatic Restart**: The Docker container is configured to automatically restart on system reboot or if the container stops unexpectedly.

## Requirements
- **Python**: The code requires Python 3.9 or higher.
- **Docker**: Docker is required to run the application inside a container.
- **Dependencies**: aiohttp, logging, and other standard Python libraries.

## Configuration
The application uses a `config.json` file for all configuration settings:

```json
{
  "log_file_path": "/app/logs/proxy_logs.log",  // Path to the log file
  "log_max_size": 10485760,                    // Maximum log file size in bytes (10MB)
  "log_backup_count": 5,                       // Number of backup log files to keep
  "reverse_proxy_map": {                       // Mapping of local IP:port to remote IP:port
    "192.168.12.2:31388": {
      "remote_ip": "Add remote IP here",
      "remote_port": 31380
    }
  },
  "server": {                                  // Server configuration
    "host": "0.0.0.0",                         // Bind to all interfaces
    "port": 31388                              // Port to listen on
  },
  "log_level": "WARNING"                       // Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
}
```

## Installation and Setup

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/reverse-proxy-with-logging.git
cd reverse-proxy-with-logging
```

### 2. Install Dependencies

If you're running the application locally (outside of Docker), create a virtual environment and install the required Python packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure the Application

Edit the `config.json` file to customize the application settings:
- Update the `reverse_proxy_map` with your local and remote IP/port combinations
- Adjust log settings as needed
- Change the server host/port if required

### 4. Dockerize the Application

The project is already set up for Docker. To run the application inside a Docker container, follow these steps:

#### Step 1: Build the Docker Image
Navigate to the project directory and build the Docker image:

```bash
docker build -t reverse-proxy-app .
```

#### Step 2: Run the Docker Container
Run the Docker container, ensuring that the logs are stored in a local directory (/path/to/local/log/directory on your machine) and mapped to /app/logs inside the container. Use the --restart flag to ensure the container restarts on system reboot or if it stops unexpectedly.

```bash
docker run -d \
  -v /path/to/local/log/directory:/app/logs \
  --restart unless-stopped \
  -p 31388:31388 \
  reverse-proxy-app
```
**Explanation**:

- `-v /path/to/local/log/directory:/app/logs`: Maps the local log directory to the container's log directory to persist logs on the host.
- `--restart unless-stopped`: Automatically restarts the container if it stops or the server is rebooted, except if the container is manually stopped.
- `-p 31388:31388`: Exposes port 31388 from the container to port 31388 on the host machine, as configured in the config.json file.

#### Step 3: Verify the Container
To check if the container is running:

```bash
docker ps
```

To view logs from the running container:

```bash
docker logs <container_id>
```

### 5. Testing the Application
After the container is running, you can send HTTP requests to http://localhost:31388 from your local clients. The server will forward these requests to the appropriate remote services based on the mappings in your config.json file and return the responses.

### 6. Log Files
Log files are stored in the directory you mapped using the -v flag when running the container. You can check the logs for any errors or warnings, including details about the client IP and the request that caused the error. The logging level can be adjusted in the config.json file.

### 7. Stopping the Container
To stop the running container, you can use:

```bash
docker stop <container_id>
```

To remove the container after stopping it:
```bash
docker rm <container_id>
```

## Usage
The reverse proxy server will:
- Listen on the port specified in config.json (default 31388) on the host machine.
- Map incoming requests from local clients to the corresponding remote services (based on mappings in config.json).
- Forward the request to the remote service and return the response to the client.
- Log messages based on the configured log level, including the client IP and request details.

## Log Rotation
The log files are automatically rotated once the file exceeds the size specified in config.json (default 10MB). The logs are stored in the directory specified in config.json inside the container, which is mapped to a directory on the host machine. Docker will ensure that the logs are persistent and remain available even if the container is removed or restarted.

## Contributing
If you'd like to contribute to this project, feel free to fork the repository, make your changes, and submit a pull request. Please ensure that you adhere to the project's coding standards and include tests for any new features or bug fixes.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact
For any inquiries or support, feel free to reach out to me via email (anubhavpatrick@gmail.com) or create an issue in the GitHub repository.