# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . auto_kmdb

# Install any needed packages specified in requirements.txt
RUN pip install -r auto_kmdb/requirements.txt

# Make port 8085 available to the world outside this container
EXPOSE 8000

# Run app.py when the container launches
CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]
