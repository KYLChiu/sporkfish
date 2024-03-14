FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update -y && \
    apt install -y --no-install-recommends \
    bash \
    binutils \
    software-properties-common \
    gnupg \
    gpg-agent \
    python3-pip
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install -y --no-install-recommends python3.13 python3.13-dev python3.13-venv
