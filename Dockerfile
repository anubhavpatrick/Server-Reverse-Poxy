# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Python application files into the container
COPY . /app

# Install the required dependencies (e.g., aiohttp)
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 31388 (the port on which the server will run)
EXPOSE 31388

# Command to run the application
CMD ["python", "app.py"]
