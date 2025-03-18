# Base image: Alpine Linux with Python 3.9
# Alpine is a minimal Linux distribution, resulting in a much smaller Docker image
FROM python:3.9-alpine

# Set the working directory inside the container to /app
# All subsequent commands will run from this directory
WORKDIR /app

# Copy all files from the build context (your local directory) into the container's /app directory
# This includes your application code and requirements.txt
COPY . /app

# Update Alpine's package index and install necessary build dependencies:
# - gcc: The GNU C compiler, needed for compiling C extensions in some Python packages
# - musl-dev: Contains development files for musl libc, needed for C compilation
# The --no-cache flag prevents storing the package index, reducing image size
RUN apk update && apk add --no-cache gcc musl-dev

# Install Python dependencies from requirements.txt
# --no-cache-dir prevents pip from using its cache, reducing image size
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 31388 to the outside world
# This is documentation - you still need to map this port when running the container
EXPOSE 31388

# Default command to run when the container starts
# This will execute "python app.py" to start your application
CMD ["python", "app.py"]