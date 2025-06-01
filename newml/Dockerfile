# Base image with Python
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install OS dependencies, including build essentials and portaudio dev for pyaudio
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the app using uvicorn
CMD ["uvicorn", "app_updated:app", "--host", "0.0.0.0", "--port", "8080"]
