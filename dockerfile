
FROM ubuntu:22.04

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    bash \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    binutils

RUN python3 -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . /app

ENV DEBIAN_FRONTEND=noninteractive

CMD ["bash"]