# Le Coffre

Le Coffre is an open-source password manager that allows you to securely store and manage passwords in a collaboration-friendly environment.

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

## ORM

When changing the database schema, you need to regenerate the migration file:

```bash
npx drizzle-kit generate
```

## TODO

- [ ] Generate encryption key when master key is created
- [ ] Setup an ORM for database (kysely) and extends better-auth model
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

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build

# Build docker
docker build -t le-coffre .
# Create a named volume
docker volume create le-coffre-volume
# Run a container using the named volume
docker run -p 3000:3000 le-coffre:latest --volume le-coffre-volume:/app
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

## Security

### Process of creation of the encryption key

During initialization, the administrator configures two essential parameters:

- The total number of shares (P) for the Master Key
- The reconstruction threshold (N), which defines the minimum number of shares needed to reconstruct the Master Key
- The system then generates two 256-bit cryptographic keys:

Master Key: Primary key which:

- Is used to encrypt the Encryption Key before storing it in the database
- Is immediately divided into P distinct shares using Shamir's algorithm
- Is never kept whole in the system after its creation

Encryption Key: Operational key which:

- Is temporarily stored in memory for encryption/decryption operations
- Is also stored in the database, but only in a form encrypted by the Master Key
- Enables the encryption and decryption of passwords and sensitive data

Shamir's algorithm ensures that at least N shares out of P are necessary to reconstruct the Master Key.
This approach provides enhanced security: even if some shares are compromised,
the Master Key remains protected as long as fewer than N shares are exposed.

When the application restarts, an unsealing process requires providing at least N shares to temporarily reconstruct the Master Key,
decrypt the Encryption Key, and place it in memory for use.

All encryption and decryption operations use the AES-256-GCM algorithm,
providing both confidentiality and data authenticity.

```mermaid
flowchart TD
    A[System initialization] -->|Admin configuration| B[Shamir parameters]
    B -->|Number of shares P & threshold N| C[Key generation]
    C -->|256 random bits| D[Master Key]
    C -->|256 random bits| E[Encryption Key]
    D -->|Encrypts| F[Encrypted Encryption Key]
    D -->|Split using Shamir| G[P shares of Master Key]
    F -->|Secure storage| H[Database]
    E -->|Temporary storage| I[Application memory]
    J[Unsealing] -->|Minimum N shares required| K[Master Key reconstruction]
    K -->|Decrypts| L[Encryption Key recovery]
    L -->|Used for| M[Password encryption/decryption]
```

### Process of encryption and decryption of a password

In this process, we asume that the DB is unseal (Encryption key is stored in memory).

```mermaid
flowchart TD
 subgraph s1["Password encryption"]
        B["IV"]
        A(["Password"])
        C["Encrypted Password"]
        D["DB"]
        E(["Encryption Key"])
        n6["Memory"]
  end
 subgraph s2["Password decryption"]
        n1["DB"]
        n2["Encrypted Password"]
        n3["IV"]
        n4["Encryption Key"]
        n5["Deciphered password"]
        n7["Memory"]
  end
    B -- Generation of random IV --> C
    C -- Stored --> D
    E --> C
    n1 --> n2 & n3
    n2 --> n5
    n3 --> n5
    n4 --> n5
    n6 --> E
    n7 --> n4
    A -- "<span style=color:>Chosen by User</span>" --> C
    B --> D
    D@{ shape: cyl}
    n6@{ shape: h-cyl}
    n1@{ shape: cyl}
    n7@{ shape: h-cyl}
```
