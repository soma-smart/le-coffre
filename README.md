# Le Coffre

<img src="frontend/public/img/le-coffre.png" alt="Le Coffre Logo" width="300">

Le Coffre is an open-source password manager that allows you to securely store and manage passwords in a collaboration-friendly environment.

## Table of Contents

- [License](#license)
- [Contributing](#contributing)
- [Security implementation](#security-implementation)
- [Init](#init)
- [ORM](#orm)
- [TODO](#todo)
- [Library used](#library-used)
- [Production deployment](#production-deployment)
- [Security considerations](#security-considerations)
- [Setup](#setup)
- [Development Server](#development-server)
- [Production](#production)
- [Security](#security)
  - [Process of creation of the encryption key](#process-of-creation-of-the-encryption-key)
  - [Process of encryption and decryption of a password](#process-of-encryption-and-decryption-of-a-password)

## License

This project is licensed under the MIT License. You are free to use, modify, and distribute this project under the terms of the license.

## Contributing

We welcome contributions from the community! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes with clear and descriptive messages.
4. Open a pull request and describe your changes.

Please read our CONTRIBUTING.md for detailed guidelines.

## Security implementation

Le Coffre uses the following security measures to ensure the safety of your passwords:

1. At initialization, a random 256-byte key is generated, Shamir is then used to split the key into P shares, N of which are needed to reconstruct the key (P, N are configurable).
2. This master key serve to encrypt the encryption key.
3. Each password is uniquely salted with a random 256-byte key generated at the time of password creation and encrypted using the encryption key.

## Init

1. Shamir process starts.
2. User is invited to create an admin account (mail, password, name).
3. Once completed, user is redirected to the admin panel where the user can setup providers, manage users,
   password entries...

## TODO

- [x] Setup an ORM for database - Using SQLModel with Alembic migrations
- [ ] Generate encryption key when master key is created
- [ ] Add a password generator
- [ ] Permission system
- [ ] Organize passwords in folders
- [ ] Customize folders (name, colors, icons)
- [ ] Add metadata to passwords (url, tags, notes, etc.)
- [ ] Search function
- [ ] Rotate passwords (notify user when password is about to expire)
- [ ] Audit log for all actions (who, when, what, where)
- [ ] Clear clipboard after a certain time
- [ ] Versioning of passwords and metadata (keep track of changes, rollback if needed)
- [ ] Add a bin for deleted passwords (soft delete)
- [ ] Allow regeneration of Shamir shares / encryption key generation and reencryption of all passwords
- [ ] Allow import/export of passwords from other password managers (Keepass, CSV, JSON, etc.)

## Library used

- Nuxt
- Nuxt UI
- Better Auth
- shamir-secret-sharing

## Production deployment

1. Behind a reverse proxy (nginx, caddy, etc.) with SSL termination.
2. Use the hardened Docker image provided.

## Security considerations

Before considering deploying Le Coffre in a production environment, please consider the following security measures:

1. The application is designed to be run in a secure environment, such as a private server or a trusted cloud provider. Any memory access is beyond threat model.
   See: https://github.com/hashicorp/vault/issues/1446 for comparable issue.
2. Limit access to the application to trusted users only. Use strong passwords and two-factor authentication (2FA) where possible.
3. Regularly update the application and its dependencies to ensure that any security vulnerabilities are patched.
4. Monitor the application for any suspicious activity, such as unauthorized access attempts or unusual behavior.
5. Regularly back up the database and other important data to prevent data loss in case of a security breach or other disaster.
6. Consider using a web application firewall (WAF) to protect the application from common web-based attacks, such as SQL injection and cross-site scripting (XSS).
7. Limit the number of users who have administrative access to the application, and regularly review user permissions to ensure that only authorized users have access to sensitive data.
8. Limit access to the application to trusted IP addresses / networks, and use a VPN or other secure connection method to access the application remotely.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

### Using Devcontainer (Recommended)

Open with VSCode and reopen in the devcontainer when prompted. The unified devcontainer includes both frontend and backend development environments with nginx as a reverse proxy.

**Quick Start:**

1. Open project in VS Code
2. Click "Reopen in Container" when prompted (VS Code will automatically detect your user's UID/GID and configure the container accordingly)
3. Use VS Code tasks to start services:
   - Press `Ctrl+Shift+P` → "Run Task" → "Start All Services"

See [.devcontainer/README.md](.devcontainer/README.md) for detailed instructions.

**Access Points:**

- **Main App:** http://127.0.0.1:8123 (via nginx - use this for development)
- Frontend (direct): http://127.0.0.1:5173
- Backend API (direct): http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs
- OpenAPI Spec: http://127.0.0.1:8000/openapi.json

> **Why nginx?** The frontend makes API calls to `/api/*` which are proxied to the backend. Always use port 8123 for development.

### Manual Setup

Within each `frontend/` or `server/` folder you will find a README.md with more details.

## Database Migrations

The backend uses Alembic for database schema management. Migrations are automatically applied on application startup.

**Manual migration commands:**

```bash
cd server

# Check current database version
alembic current

# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Rollback the last migration
alembic downgrade -1
```

See [server/alembic/README.md](server/alembic/README.md) for detailed migration documentation.

## Production

Build the application for production:

```bash
# Build docker
docker build -t le-coffre .
# Create a named volume
docker volume create le-coffre-volume
# Run a container using the named volume
docker run -p 3000:3000 le-coffre:latest --volume le-coffre-volume:/app

# Pull docker image
docker pull rg.fr-par.scw.cloud/soma-smart-cr/le-coffre:latest
```
