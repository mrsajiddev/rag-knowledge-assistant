# Engineering handbook

How the Nestora engineering team builds, ships and runs software. Owner: Omar Farooq, VP Engineering.

## Tech stack

- **Core platform** (dashboard, storefront rendering, admin APIs): PHP 8.3 with Laravel 11, MySQL 8 with read replicas, Redis for cache and queues, and Laravel Horizon for queue workers.
- **Dashboard front end**: Vue 3 with TypeScript and Vite.
- **Services** (checkout, NestPay ledger, webhooks dispatcher, Nestora Ship integrations): Node.js 20 with TypeScript and Fastify, using PostgreSQL for the payments ledger.
- **Search**: OpenSearch for storefront product search.
- **Infrastructure**: AWS (Bahrain region), Kubernetes (EKS), Terraform for all infrastructure, and Cloudflare in front of storefronts.
- **Observability**: OpenTelemetry tracing, Grafana dashboards and PagerDuty-style on-call alerting.

## Repositories and branching

Code lives in GitHub. Each service has its own repository; the Laravel core is a single repository called `platform`. The main branch is `main` and is always deployable. Work happens in short-lived feature branches named `type/TICKET-short-description`, for example `fix/PAY-412-payout-rounding`.

## Code review

- Every change needs a pull request and at least **one approving review**. Changes to payments, authentication or the database schema need **two** approvals, one from a code owner.
- Pull requests should be under 400 changed lines where possible.
- CI must pass: unit tests, static analysis (PHPStan level 8 for PHP, `tsc --strict` for TypeScript), linting and a security dependency scan.
- Reviewers should respond within **one working day**.

## Testing

New code needs automated tests. The team aims for at least 80% line coverage on services and requires tests for every bug fix. End-to-end checkout tests run against a staging store before every production deploy.

## Deployments

- Deploys go out through the CI/CD pipeline; nobody deploys from a laptop.
- Production deploys happen **Monday to Thursday, 10:00 AM to 4:00 PM PKT**. There are no deploys on Fridays, weekends or public holidays except for urgent fixes approved by the on-call lead.
- Every deploy goes first to staging, then to a 5% canary for 30 minutes, then to all traffic.
- Feature flags are used for anything merchants can see, so features can be turned off without a rollback.
- Database migrations must be backwards compatible with the previous release (expand, migrate, then contract).

## On-call

Each team runs a weekly on-call rotation that starts on Monday at 10:00 AM. The primary on-call engineer must acknowledge pages within **10 minutes** and be able to start working within 30 minutes. On-call engineers receive an allowance of PKR 25,000 per week, and a day off in lieu after any night with more than two hours of incident work.

## Incident severity

| Severity | Definition | Response |
|---|---|---|
| SEV1 | Checkout, payments or all storefronts down | Page on-call immediately; incident commander assigned; status page updated within 15 minutes |
| SEV2 | Major feature broken for many merchants | Page on-call; status page updated within 30 minutes |
| SEV3 | Partial degradation or a workaround exists | Handled in working hours |
| SEV4 | Minor bug, no merchant impact | Normal backlog |

Every SEV1 and SEV2 incident gets a blameless post-mortem, written within **5 working days**, with action items tracked to completion.

## Security practices

- Secrets are stored in the secrets manager, never in code or `.env` files committed to Git.
- Production database access requires a just-in-time access request and is logged.
- Dependencies are scanned daily; critical vulnerabilities must be patched within 7 days.
- Every engineer completes secure-coding training once a year.

## Onboarding for new engineers

In their first week, new engineers set up the local environment with `make bootstrap` (Docker-based), ship a small change to production, and shadow the on-call engineer for one day. Each new engineer has an onboarding buddy for the first 30 days.
