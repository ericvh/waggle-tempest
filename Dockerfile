FROM waggle/plugin-base:1.1.1-base

# Install system dependencies for network access
RUN apt-get update && apt-get install -y \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy plugin source code
COPY main.py /app/

# Set the working directory
WORKDIR /app

# Make the main script executable
RUN chmod +x main.py

# Set default environment variables
ENV TEMPEST_PROTOCOL=tcp
ENV TEMPEST_TCP_PORT=50222
ENV TEMPEST_UDP_PORT=50222
ENV TEMPEST_PUBLISH_INTERVAL=60
ENV TEMPEST_DEBUG=false

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Default values\n\
PROTOCOL="${TEMPEST_PROTOCOL:-tcp}"\n\
TCP_PORT="${TEMPEST_TCP_PORT:-50222}"\n\
UDP_PORT="${TEMPEST_UDP_PORT:-50222}"\n\
PUBLISH_INTERVAL="${TEMPEST_PUBLISH_INTERVAL:-60}"\n\
DEBUG="${TEMPEST_DEBUG:-false}"\n\
\n\
echo "🌤️  Tempest Weather Station Waggle Plugin Starting..."\n\
echo "Protocol: ${PROTOCOL^^}"\n\
if [ "$PROTOCOL" = "tcp" ]; then\n\
    echo "TCP Port: $TCP_PORT"\n\
    echo "✓ Container ready for TCP connections with length-prefixed messages"\n\
else\n\
    echo "UDP Port: $UDP_PORT"\n\
    if [ -w /proc/sys/net ] 2>/dev/null; then\n\
        echo "✓ Container has network privileges for UDP listening"\n\
    else\n\
        echo "⚠️  Warning: Limited network privileges"\n\
        echo "   UDP listening may not work properly"\n\
        echo "   Consider using: --network host"\n\
    fi\n\
fi\n\
echo "Publish Interval: $PUBLISH_INTERVAL seconds"\n\
echo "Debug Mode: $DEBUG"\n\
echo ""\n\
\n\
# Build command line arguments\n\
ARGS=("--protocol" "$PROTOCOL" "--publish-interval" "$PUBLISH_INTERVAL")\n\
\n\
if [ "$PROTOCOL" = "tcp" ]; then\n\
    ARGS+=("--tcp-port" "$TCP_PORT")\n\
else\n\
    ARGS+=("--udp-port" "$UDP_PORT")\n\
fi\n\
\n\
if [ "$DEBUG" = "true" ]; then\n\
    ARGS+=("--debug")\n\
fi\n\
\n\
# Add any additional arguments passed to the container\n\
ARGS+=("$@")\n\
\n\
# Run the Tempest plugin\n\
exec python3 /app/main.py "${ARGS[@]}"\n\
' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden)
CMD []

