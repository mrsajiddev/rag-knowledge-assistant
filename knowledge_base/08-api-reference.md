# REST API reference (v2)

The Nestora REST API lets developers read and write store data. API v2 became generally available in release 6.0 (March 2026). API v1 is deprecated and will be switched off on **31 March 2027**.

## Base URL

```
https://api.nestora.example/v2
```

All requests must use HTTPS. Request and response bodies are JSON encoded in UTF-8. Timestamps use ISO 8601 in UTC, and money amounts are strings in the store currency with two decimals, for example `"1499.00"`.

## Authentication

Create an API key in **Settings > Developers > API keys**. Only the store owner and staff with the Developer permission can create keys. A key is shown once; store it securely. Send it as a bearer token:

```
Authorization: Bearer nsk_live_9f2c...
```

Keys starting with `nsk_test_` only work against the test-mode data of the store. A missing or invalid key returns `401` with error NS-1001. A revoked key returns error NS-1003.

### Scopes

Each key has scopes that limit what it can do. A request without the right scope returns `403` with error NS-1002.

- `read_products`, `write_products`
- `read_orders`, `write_orders`
- `read_customers`, `write_customers`
- `read_inventory`, `write_inventory`
- `read_fulfillments`, `write_fulfillments`
- `manage_webhooks`

## Rate limits

Rate limits depend on the plan: 2 requests per second on Starter, 5 on Growth, 20 on Scale and 50 on Enterprise, with bursts of up to twice that rate. Every response includes these headers:

- `X-RateLimit-Limit`: requests allowed per second
- `X-RateLimit-Remaining`: requests left in the current window
- `X-RateLimit-Reset`: seconds until the window resets

When the limit is exceeded the API returns `429 Too Many Requests` with error NS-1429 and a `Retry-After` header. Clients should wait for the given number of seconds and retry with exponential backoff.

## Pagination

List endpoints use cursor pagination. Pass `limit` (default 50, maximum 250) and the `cursor` from the previous response:

```
GET /v2/orders?limit=100&cursor=eyJpZCI6MTIzNDV9
```

The response contains `data` (the items) and `next_cursor`, which is `null` on the last page.

## Main endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/products` | List products. Filters: `status`, `collection_id`, `updated_since` |
| POST | `/products` | Create a product with variants |
| GET | `/products/{id}` | Get one product |
| PATCH | `/products/{id}` | Update a product |
| DELETE | `/products/{id}` | Delete a product |
| GET | `/orders` | List orders. Filters: `payment_status`, `fulfillment_status`, `created_since` |
| GET | `/orders/{id}` | Get one order |
| POST | `/orders/{id}/cancel` | Cancel an unfulfilled order |
| POST | `/orders/{id}/refunds` | Create a full or partial refund |
| POST | `/orders/{id}/fulfillments` | Mark items as shipped, with tracking |
| GET | `/customers` | List customers. Filter: `email`, `phone` |
| POST | `/inventory/adjustments` | Adjust stock for a variant at a location |
| GET | `/webhooks` / POST `/webhooks` | List or create webhook subscriptions |

## Example: create a product

```bash
curl -X POST https://api.nestora.example/v2/products \
  -H "Authorization: Bearer $NESTORA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Khaddar Kurta",
    "status": "active",
    "options": ["Size"],
    "variants": [
      {"sku": "KK-S", "price": "3499.00", "option1": "S", "inventory_qty": 20},
      {"sku": "KK-M", "price": "3499.00", "option1": "M", "inventory_qty": 35}
    ]
  }'
```

## Idempotency

`POST` requests accept an `Idempotency-Key` header (any unique string up to 64 characters). If a request is retried with the same key within 24 hours, the API returns the original response instead of creating a duplicate. Always use idempotency keys when creating refunds.

## Errors

Errors use standard HTTP status codes and a JSON body:

```json
{"error": {"code": "NS-2001", "message": "SKU 'KK-S' already exists", "request_id": "req_7Hq2..."}}
```

Include the `request_id` when contacting support. See the error codes reference for every `NS-` code.
