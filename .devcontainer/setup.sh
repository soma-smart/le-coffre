#!/bin/bash
# This script is run by VS Code devcontainer before building
# It exports the current user's UID and GID for the Docker build

export USER_UID=$(id -u)
export USER_GID=$(id -g)

echo "Building devcontainer with USER_UID=${USER_UID} and USER_GID=${USER_GID}"
