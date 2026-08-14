FROM python:3.12-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Install Playwright and Chromium with system dependencies
RUN playwright install --with-deps chromium

# Copy the entire project into the container
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Run the entrypoint script by default
CMD ["./entrypoint.sh"]
