# DjShrek-Draiver Cyber Club — license service

## Current status

- Public purchase page: `docs/license/index.html`
- Price displayed: **200 RUB / 1 calendar year**
- Payment method planned: **SBP**
- Payment provider and merchant credentials: **not configured**
- Live checkout and automatic post-payment delivery: **not enabled**
- License API starter: Python standard library + SQLite

Do not accept money or promise automatic delivery until a legal merchant account,
SBP acquiring provider, verified webhook and production HTTPS deployment are configured.

## License rules implemented in the API starter

- Keys contain exactly 20 characters from an unambiguous 32-character alphabet.
- Cryptographically secure random generation (`secrets`).
- Only SHA-256 hashes are stored in SQLite; plaintext is displayed once at issuance.
- Activation is atomic (`BEGIN IMMEDIATE`) and only succeeds while status is `unused`.
- First successful activation binds the key to a machine identifier hash.
- Expiry is one calendar year after activation; 29 February rolls to 28 February.
- Subsequent activation attempts are rejected. Verification is allowed for the bound machine.

## Run locally

Python 3.11+; no third-party packages required.

```bash
cd license-server
python server.py --init
python server.py --serve
```

The API listens on 127.0.0.1:8765 by default.

### Activate

```http
POST /v1/activate
Content-Type: application/json

{"key":"YOUR20CHARACTERKEY","machine_id":"stable-installation-id"}
```

### Verify

```http
POST /v1/verify
Content-Type: application/json

{"key":"YOUR20CHARACTERKEY","machine_id":"stable-installation-id"}
```

### Issue one key after confirmed payment

Only an operator or trusted payment-webhook worker should run this command after checking the provider's signed webhook and confirming the payment amount is exactly 200 RUB and its status is paid:

```bash
python server.py --issue --payment-reference PROVIDER_PAYMENT_ID
```

The command prints the key once. Deliver it to the buyer through a protected channel. A unique payment reference prevents issuing twice for the same order.

## Production requirements still outstanding

1. Select an SBP acquiring provider and complete merchant onboarding.
2. Implement that provider's exact signed-webhook verification; verify amount=200 RUB, currency=RUB, paid status, order ID and replay/idempotency before issuing.
3. Add order creation, buyer email delivery and retry-safe delivery records.
4. Deploy behind HTTPS reverse proxy with firewall, backups, monitoring and rate limiting.
5. Move the database to managed PostgreSQL for production scale; SQLite is a starter for testing, not a billion-record production system.
6. Add API authentication/rate limits and server-side audit logs that never contain plaintext license keys.
7. Integrate the desktop application with `/v1/activate` and `/v1/verify`; do not trust client-side expiry alone.

## About one billion keys

Do **not** commit a billion-key text file to GitHub. It would be enormous, expose all saleable keys, and be impractical to manage. Generate keys on demand after verified payment. The keyspace is 32^20 (about 1.27e30 combinations); collision checks and a unique database constraint protect issuance.
