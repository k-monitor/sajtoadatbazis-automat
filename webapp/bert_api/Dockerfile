# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
RUN huggingface-cli download 'boapps/kmdb_classification_model'

# Make port 8085 available to the world outside this container
EXPOSE 8000

# Define environment variable TODO
ENV THRESHOLD 0.42

# Run app.py when the container launches
CMD ["gunicorn", "bert_api:app", "--bind", "0.0.0.0:8000"]
