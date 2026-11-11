# Security, privacy and data

## Account security

- **Two-factor authentication (2FA)** has been mandatory for store owners since release 5.2 (June 2025). Staff accounts can be required to use 2FA in **Settings > Users > Security**.
- **Single sign-on (SAML 2.0)** is available on the Enterprise plan and works with common identity providers.
- **Staff permissions** control access to orders, products, customers, reports, settings and developer tools. Only the store owner can change billing or close the store.
- **Session security**: sessions expire after 14 days of inactivity, and owners can sign out all devices from **Settings > Users**.
- **Activity log**: every change to settings, staff, payments and API keys is recorded for 1 year (2 years on Enterprise).

## Payment security

NestPay is certified **PCI DSS Level 1**. Card details are entered in Nestora-hosted fields and never touch the merchant's server or theme code, so merchants do not need their own PCI certification for card payments. All card payments use 3-D Secure where the issuing bank supports it.

## Infrastructure and encryption

- Store data is hosted on AWS in the Middle East (Bahrain) region, with encrypted backups replicated to the EU (Frankfurt) region.
- Data is encrypted in transit with TLS 1.2 or newer and at rest with AES-256.
- Full database backups run every day and are kept for 30 days. Point-in-time recovery covers the last 7 days.
- Production access is limited to the on-call infrastructure team and requires hardware security keys.

## Privacy

Merchants own their store data and their customers' data. Nestora processes customer data only to provide the service, and never sells it. The Data Processing Addendum is available to all merchants in **Settings > Legal**.

Customers of a store can ask the merchant to export or delete their personal data. Merchants handle these requests from the customer's profile with **Export data** or **Erase personal data**. Erasure removes the customer's name, email, phone and addresses from orders while keeping the order totals needed for accounting.

## Data retention

- Active stores: data is kept for as long as the store is open.
- Closed stores and stores whose trial ended without a plan: data is kept for **90 days** and then permanently deleted, including backups after their 30-day cycle.
- Webhook delivery logs: 7 days. API request logs: 30 days.

## Data export

The store owner can export products, customers, orders, inventory and reports at any time from **Settings > Data export**, in CSV or JSON format. Large exports are emailed as a download link that stays valid for 72 hours.

## Reporting a vulnerability

Report security issues to security@nestora.example. Nestora runs a responsible disclosure programme with rewards from USD 100 to USD 5,000 depending on severity. Do not test against stores you do not own; create a free trial store for testing.
