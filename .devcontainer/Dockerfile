FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN rm -rf /var/lib/apt/lists/* && \
    apt-get update -y &&  \
    apt-get install -y --no-install-recommends \
    software-properties-common
RUN apt update -y && \
    apt install -y --no-install-recommends \
    binutils \   
    gnupg \
    gpg-agent 
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install -y --no-install-recommends --fix-missing \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-pip

RUN echo "alias python='python3.12'" >> ~/.bashrc
RUN echo "alias python3='python3.12'" >> ~/.bashrc