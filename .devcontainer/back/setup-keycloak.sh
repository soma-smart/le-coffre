#!/bin/bash

# Script to configure Keycloak for integration tests
# This runs inside the devcontainer and configures Keycloak that's running as a separate service

set -e

echo "🔧 Configuring Keycloak for integration tests..."

KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
REALM_NAME="master"
CLIENT_ID="lecoffre-test-client"
TEST_USERNAME="testuser"
TEST_PASSWORD="testpass123"
TEST_EMAIL="testuser@example.com"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin"

# Wait for Keycloak to be ready
echo "⏳ Waiting for Keycloak to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -sf "${KEYCLOAK_URL}/health/ready" > /dev/null 2>&1; then
        echo "✅ Keycloak is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Keycloak failed to become ready"
    exit 1
fi

# Get admin access token
echo "🔐 Getting admin access token..."
TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=${ADMIN_USERNAME}" \
    -d "password=${ADMIN_PASSWORD}" \
    -d "grant_type=password")

ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ Failed to get admin token"
    echo "$TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Got admin token"

# Create test user
echo "👤 Creating test user: ${TEST_USERNAME}..."
USER_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "username": "'"${TEST_USERNAME}"'",
        "email": "'"${TEST_EMAIL}"'",
        "enabled": true,
        "emailVerified": true,
        "firstName": "Test",
        "lastName": "User",
        "credentials": [{
            "type": "password",
            "value": "'"${TEST_PASSWORD}"'",
            "temporary": false
        }]
    }')

HTTP_CODE=$(echo "$USER_CREATE_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "201" ]; then
    echo "✅ Test user created"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "ℹ️  Test user already exists, resetting password..."
    # Get user ID
    USERS_RESPONSE=$(curl -s "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users?username=${TEST_USERNAME}" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}")
    USER_ID=$(echo "$USERS_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -n "$USER_ID" ]; then
        curl -s -X PUT "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users/${USER_ID}/reset-password" \
            -H "Authorization: Bearer ${ADMIN_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{
                "type": "password",
                "value": "'"${TEST_PASSWORD}"'",
                "temporary": false
            }'
        echo "✅ Password reset for existing user"
    fi
else
    echo "⚠️  User creation status: ${HTTP_CODE}"
fi

# Create OIDC client
echo "🔧 Creating OIDC client: ${CLIENT_ID}..."
CLIENT_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "clientId": "'"${CLIENT_ID}"'",
        "enabled": true,
        "publicClient": false,
        "redirectUris": ["http://localhost:8000/auth/sso/callback"],
        "webOrigins": ["http://localhost:8000"],
        "protocol": "openid-connect",
        "standardFlowEnabled": true,
        "directAccessGrantsEnabled": false,
        "serviceAccountsEnabled": false,
        "fullScopeAllowed": true
    }')

HTTP_CODE=$(echo "$CLIENT_CREATE_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "201" ]; then
    echo "✅ Client created"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "ℹ️  Client already exists"
else
    echo "⚠️  Client creation status: ${HTTP_CODE}"
fi

# Get client secret
echo "🔑 Retrieving client secret..."
CLIENTS_RESPONSE=$(curl -s "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients?clientId=${CLIENT_ID}" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")
CLIENT_UUID=$(echo "$CLIENTS_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -n "$CLIENT_UUID" ]; then
    SECRET_RESPONSE=$(curl -s "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients/${CLIENT_UUID}/client-secret" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}")
    CLIENT_SECRET=$(echo "$SECRET_RESPONSE" | grep -o '"value":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$CLIENT_SECRET" ]; then
        echo "✅ Client secret retrieved"
        
        # Save configuration to a file for tests to use
        cat > /tmp/keycloak-test-config.env << EOF
KEYCLOAK_URL=${KEYCLOAK_URL}
KEYCLOAK_REALM=${REALM_NAME}
KEYCLOAK_CLIENT_ID=${CLIENT_ID}
KEYCLOAK_CLIENT_SECRET=${CLIENT_SECRET}
KEYCLOAK_TEST_USERNAME=${TEST_USERNAME}
KEYCLOAK_TEST_PASSWORD=${TEST_PASSWORD}
KEYCLOAK_TEST_EMAIL=${TEST_EMAIL}
EOF
        echo "✅ Configuration saved to /tmp/keycloak-test-config.env"
    fi
fi

echo "🎉 Keycloak configuration complete!"
echo ""
echo "Configuration details:"
echo "  - Keycloak URL: ${KEYCLOAK_URL}"
echo "  - Realm: ${REALM_NAME}"
echo "  - Client ID: ${CLIENT_ID}"
echo "  - Test User: ${TEST_USERNAME}"
echo "  - Test Password: ${TEST_PASSWORD}"
echo ""
