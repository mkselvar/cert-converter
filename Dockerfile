# Use Red Hat UBI Python 3.9
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
    PORT=5000

# Create application directory
WORKDIR ${APP_HOME}

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create OpenShift-compatible user
RUN chgrp -R 0 ${APP_HOME} && \
    chmod -R g=u ${APP_HOME} && \
    chmod -R +x ${APP_HOME}/RUN

# Set OpenShift-compatible permissions
RUN chmod -R ug+rwx ${APP_HOME} && \
    chown -R 1001:0 ${APP_HOME}

# Switch to non-root user
USER 1001

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run script
CMD ["./RUN"]
