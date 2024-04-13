# This Dockerfile is used for building the image for production
FROM python:3.11-bookworm

ENV APP_HOME /app
WORKDIR ${APP_HOME}
COPY . ./

# Install core dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    musl-dev \
    libffi-dev \
    libssl-dev

# Install python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Run the application
ENTRYPOINT [ "python3" ]
CMD ["-O", "main.py"]
