# ---- Base Stage ----
# Use an official Python runtime as a parent image.
# Choose a specific version and a 'slim' variant for smaller size.
# 'bullseye' refers to the Debian version.
FROM python:3.10-slim-bullseye as base

# Set environment variables to prevent Python from writing pyc files (optional, saves space)
# and prevent buffering of stdout/stderr (good for logging in containers)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# ---- Builder Stage ----
# Separate stage for installing dependencies to leverage Docker cache better.
FROM base as builder

# Install build dependencies if needed (e.g., for packages that compile C code)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev

# Copy only the requirements file first
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not storing the pip download cache
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime Stage ----
# Final stage, copy only what's needed from the builder stage and the app code.
FROM base as runtime

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create a non-root user and group for security
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot
# Ensure the app directory exists and set ownership (if WORKDIR didn't create it fully)
RUN mkdir -p /app && chown -R nonroot:nonroot /app
USER nonroot

# Copy the application code into the container
# Ensure this COPY happens *after* setting WORKDIR and potentially after USER if permissions matter early
COPY . .

# Expose the port the app runs on (Gunicorn default or specified in CMD)
# This informs Docker that the container listens on this port. You still need -p when running.
EXPOSE 5000

# Define the command to run the application using Gunicorn
# --bind 0.0.0.0 makes the app accessible from outside the container
# app:app refers to the 'app' instance inside the 'app.py' module
# Adjust 'app:app' if your file or instance variable name is different.
# Use environment variables for flexibility if needed (e.g., $PORT)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

# --- Alternative CMD using Flask Development Server (NOT recommended for anything beyond basic testing) ---
# If you absolutely must use the dev server (e.g., no gunicorn):
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0
# ENV FLASK_RUN_PORT=5000
# CMD ["flask", "run"]
# ------------------------------------------------------------------------------------------------------
