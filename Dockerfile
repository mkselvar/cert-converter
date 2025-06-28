FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && \
    apt-get update && \
    apt-get install -y openssl default-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]