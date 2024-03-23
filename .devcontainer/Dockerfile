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
RUN apt update -y && apt-get update -y
RUN apt install -y --no-install-recommends python3.12 python3.12-dev python3.12-venv

RUN echo "alias python='python3.12'" >> ~/.bashrc
RUN echo "alias python3='python3.12'" >> ~/.bashrc

CMD ["bash"]