FROM python:3.12-slim
WORKDIR /app/main
COPY ./requirements.txt ./
COPY ./requirements_dev.txt ./
RUN pip install --no-cache-dir -r requirements_dev.txt