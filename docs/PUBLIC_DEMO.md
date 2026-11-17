# Public-demo deployment package

The public entry point is `genesis.public:public_app`. It uses signed HttpOnly session cookies and separate visitor SQLite databases, accepts only the bundled synthetic actor/source model with policy/revision variations, disables external AI requests, limits bodies to 64 KiB, limits verification to depth 3 and 1 second per check, permits two operations at once with a one-second queue deadline, and caps sessions, requests and per-session database size. Rejected input is checked before a visitor session is allocated. Visitor sessions expire after an hour, and stale orphan databases are removed on startup. No ServiceNow connection is present.

Required private configuration: `GENESIS_SESSION_SECRET` (at least 32 random characters), `GENESIS_PUBLIC_DATA` (private writable storage), and either `RENDER_EXTERNAL_HOSTNAME` or `GENESIS_PUBLIC_HOST` (comma-separated exact hostnames, including any custom domain). HTTPS is required by default. Run exactly one worker; in-memory quotas are not a distributed rate limiter. Restarting intentionally discards visitor sessions. Never expose `genesis.api:app` as the public entry point.

`Dockerfile` and `render.yaml` prepare a Render deployment. Render was selected because its web service supports Docker, managed HTTPS, health checks and custom domains. The free service is suitable for a portfolio demo but can sleep after inactivity and uses ephemeral storage; that is acceptable because GENESIS visitor data is deliberately temporary. The app also has process-local global and per-session limits; Render supplies edge DDoS mitigation, but this is not a high-traffic production architecture.

Example launch after private configuration:

```sh
GENESIS_PUBLIC_REQUIRE_HTTPS=false GENESIS_SESSION_SECRET=<private-random-value> python -m genesis.serve
```

For Render, connect the repository and create a Blueprint from `render.yaml`. Render generates the cookie-signing secret and its `onrender.com` hostname automatically. Add a custom domain later in Render and include it in `GENESIS_PUBLIC_HOST`; Render provisions and renews TLS and redirects HTTP to HTTPS. The container trusts forwarded headers from all direct peers only because Render's service port is not directly internet-accessible; change `GENESIS_FORWARDED_ALLOW_IPS` if using a different proxy topology.

## Live deployment

The public demo is deployed at https://genesis-workflow-demo.onrender.com/ from the public repository https://github.com/balu44445/genesis-workflow-twin. On November 17, 2026, the hosted release passed the vulnerable two-step counterexample, corrected self-approval rejection with unchanged pending state, Alice→Bob→Carol fulfillment, and isolation between separate browser cookie stores. Live HTTPS checks returned HSTS, strict CSP, framing denial, no-referrer, restricted browser permissions, opener isolation, no-store and nosniff headers; `/docs` and `/openapi.json` returned 404. External AI and ServiceNow writes remain disabled.

No custom domain has been purchased or configured. The free Render service can sleep after inactivity. This is a portfolio demonstration, not a high-traffic or production ServiceNow control plane.
