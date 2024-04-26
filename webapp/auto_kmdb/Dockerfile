# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . auto_kmdb

# Install any needed packages specified in requirements.txt
RUN pip install -r auto_kmdb/requirements.txt
RUN python auto_kmdb/init_container.py
RUN apt update
RUN apt install -y wget
RUN mkdir /models
RUN wget 'https://huggingface.co/boapps/kmdb-category-classifier/resolve/main/svm_classifier_category.joblib?download=true' -O /models/svm_classifier_category.joblib

ENV DATA_PATH="/data"

# Make port 8085 available to the world outside this container
EXPOSE 8000

# Run app.py when the container launches
CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]
