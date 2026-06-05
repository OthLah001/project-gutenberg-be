# Set the base image builder
FROM python:3.12-slim

# Create working directory and accessing it
RUN mkdir /app
WORKDIR /app

# Prevent writing pyc, stdout, and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential gcc libpq-dev python3-dev && rm -rf /var/lib/apt/lists/*
RUN which pg_config
RUN pg_config --version

# Upgrade pip
RUN pip install --upgrade pip

# Copy dependencies and install them
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the code and run it
COPY . /app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]