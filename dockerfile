# Use the official Ubuntu base image
FROM ubuntu:latest

CMD pwd

# # Set the working directory to the current working directory
# WORKDIR ../lichess-bot
# COPY . /app/lichess-bot


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
    binutils

# Update pip and install any Python packages you need
RUN python3 -m pip install --upgrade pip

RUN pip install -r requirements.txt

CMD ["bash"]