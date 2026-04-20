# syntax=docker/dockerfile:1
# check=skip=critical_high_vulnerabilities

FROM python:3.10-slim-trixie

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./src .

EXPOSE 10002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10002"]
