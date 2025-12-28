FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for serial communication
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Set working directory to AlertBot
WORKDIR /app/scripts/AlertBot

# Create default config file with container device path
RUN echo '{"port": "/dev/ttyUSB0"}' > .config.json

# Create logs directory
RUN mkdir -p logs

# Default command (can be overridden)
CMD ["python", "bot.py"]

