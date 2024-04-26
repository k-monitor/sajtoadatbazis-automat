# Use an official Python runtime as a parent image
FROM alpine

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN apk add --update --no-cache wget

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . auto_kmdb

# Install any needed packages specified in requirements.txt
RUN pip3 install -r auto_kmdb/requirements.txt
RUN python3 auto_kmdb/init_container.py
RUN mkdir /models
RUN wget 'https://huggingface.co/boapps/kmdb-category-classifier/resolve/main/svm_classifier_category.joblib?download=true' -O /models/svm_classifier_category.joblib

ENV DATA_PATH="/data"

# Make port 8085 available to the world outside this container
EXPOSE 8000

# Run app.py when the container launches
CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]
