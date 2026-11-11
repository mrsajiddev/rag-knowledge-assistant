# Error codes reference

Nestora errors start with `NS-` followed by four digits. The first digit shows the area: 1 for authentication and limits, 2 for catalogue, 3 for payments, 4 for shipping, 5 for domains, 6 for webhooks.

## Authentication and limits (NS-1xxx)

### NS-1001: Invalid API key
The `Authorization` header is missing, malformed or contains an unknown key. Check that the header is `Authorization: Bearer <key>` and that you are not using a test key (`nsk_test_`) against live data.

### NS-1002: Missing scope
The key is valid but lacks the scope for this endpoint, for example calling `POST /v2/refunds` without `write_orders`. Edit the key's scopes in **Settings > Developers > API keys**, or create a new key.

### NS-1003: API key revoked
The key was revoked by a staff member, or automatically after the staff member who created it was removed from the store. Create a new key.

### NS-1429: Rate limit exceeded
Too many requests per second for your plan. Wait for the number of seconds in the `Retry-After` header, then retry with exponential backoff. The official SDKs do this automatically.

## Catalogue (NS-2xxx)

### NS-2001: SKU already exists
SKUs must be unique within a store. Change the SKU, or update the existing variant instead of creating a new one.

### NS-2002: Variant limit exceeded
A product can have at most 3 options and 100 variants. Split the product into several products, for example one per colour.

### NS-2003: Image too large
Images must be at most 20 MB and 4472 × 4472 pixels. Resize the image and upload it again.

### NS-2101: CSV column missing
The import file is missing a required column (`handle`, `title`, `sku` or `price`). Nothing was imported. Add the column and upload the file again.

## Payments (NS-3xxx)

### NS-3001: Payment declined by issuer
The customer's bank declined the card. Nestora does not receive the exact reason. Ask the customer to use another card or a different payment method.

### NS-3002: NestPay account under review
NestPay's risk team is reviewing the account, usually because of a sudden change in sales volume or a high dispute rate. Payouts are paused, but the store can still take payments. Reviews normally finish within 3 business days; respond quickly to any document requests.

### NS-3005: Payout bank account verification failed
The bank account could not be verified, usually because the account title does not match the verified business or owner name, or the IBAN is wrong. Update the account in **Settings > Payments > Payouts**. Payouts resume after the new account is verified.

## Shipping (NS-4xxx)

### NS-4001: Area not serviceable
The chosen courier does not deliver to the destination postcode or city. Try another courier.

### NS-4002: Pickup cut-off missed
Same-day pickup must be booked before 2:00 PM local time on a working day. The booking is moved to the next working day.

### NS-4012: COD limit exceeded
The order total is above the COD maximum: PKR 150,000 platform-wide, or the lower limit set by the merchant. The customer must pay online.

## Domains (NS-5xxx)

### NS-5001: Domain DNS not verified
The domain's DNS records do not point to Nestora yet. Check the `A` record (`203.0.113.40`) and the `www` `CNAME` (`stores.nestora.example`). Propagation can take up to 48 hours.

### NS-5002: SSL certificate pending
DNS is verified and the certificate is being issued. This usually takes under an hour and can take up to 24 hours. If it is still pending after 24 hours, check for a `CAA` record that blocks the certificate authority, and contact support.

## Webhooks (NS-6xxx)

### NS-6001: Webhook signature invalid
Shown in your own logs when the signature check fails. Compute the HMAC-SHA256 over `timestamp + "." + raw_body` before any JSON parsing, and make sure you use the signing secret of the right subscription.

### NS-6002: Webhook endpoint disabled
The endpoint failed every delivery for 3 consecutive days and was disabled. Fix the endpoint, re-enable it, then re-send missed events from the delivery log (kept for 7 days).
