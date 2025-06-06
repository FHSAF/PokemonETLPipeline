# Dockerfile

# Step 1
FROM python:3.11-slim

# Step 2: Set environment variables for best practices in Python containers.
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files.
# PYTHONUNBUFFERED: Ensures Python output (e.g., logs) is sent directly to the terminal.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Step 3: Set the working directory inside the container.
WORKDIR /app

# Step 4: Copy the requirements file into the container.
COPY requirements.txt .

# Step 5: Install the Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Copy the entire application source code into the container.
COPY . .

# Step 7: Expose the port that the Streamlit application will run on.
EXPOSE 8501

# Step 8: Define the default command to run when the container starts.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]