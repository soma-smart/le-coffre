FROM node:22-bullseye-slim

# Install Python and other useful tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install pre-commit

# Verify installations
RUN node --version && npm --version && python3 --version && pip3 --version

# Set working directory
WORKDIR /workspace

# Expose port 3000
EXPOSE 3000

# Set ENV to DEV
ENV ENV=DEV

# Default command
CMD ["bash"]
