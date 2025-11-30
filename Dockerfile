# Use official Python runtime
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port 8080 (Cloud Run standard)
EXPOSE 8080

# Run the app using Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]