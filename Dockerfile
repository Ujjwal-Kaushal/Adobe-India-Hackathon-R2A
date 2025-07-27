# Use a specific, lightweight Python image with linux/amd64 platform to ensure compatibility.
FROM --platform=linux/amd64 python:3.9-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the file with dependencies first to leverage Docker's layer caching.
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python script into the container at the working directory /app
COPY extract_outline.py .

# The command to run your script when the container starts.
# This will execute the process_pdfs() function in your script.
CMD ["python", "extract_outline.py"]