# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
#ENV BANDIT_MODE="rank_multi_armed_bandit"
#ENV DB_TYPE="sqlite"
#ENV DB_PATH="/app/instance/recommender.db"
# For PostgreSQL (example, adjust as needed)
# ENV DB_URL="postgresql_host"
# ENV DB_USER="user"
# ENV DB_PASS="password"
# ENV DB_NAME="recommender"

# Run main.py when the container launches
CMD ["python", "main.py"]
