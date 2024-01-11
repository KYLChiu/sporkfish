# Use the official Ubuntu base image
FROM ubuntu:latest

CMD pwd

WORKDIR /app

# Copy your application code into the container
COPY . /app

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Update the package lists and install necessary packages
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    bash \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \ 
    pypy3 \
    binutils

# Update pip and install any Python packages you need
RUN python3 -m pip install --upgrade pip
RUN pypy3 -m pip install --upgrade pip

RUN pip install -r requirements.txt

CMD ["bash"]