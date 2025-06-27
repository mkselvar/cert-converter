FROM registry.access.redhat.com/ubi8/python-39:latest

USER root
# Install system dependencies
RUN yum install -y --setopt=tsflags=nodocs \
    openssl \
    java-11-openjdk-headless && \
    yum clean all && \
    rm -rf /var/cache/yum

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    APP_HOME=/app \
    PORT=8080

WORKDIR ${APP_HOME}

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set permissions
RUN chgrp -R 0 ${APP_HOME} && \
    chmod -R g=u ${APP_HOME} && \
    chmod +x ${APP_HOME}/RUN

USER 1001

EXPOSE ${PORT}

CMD ["./RUN"]