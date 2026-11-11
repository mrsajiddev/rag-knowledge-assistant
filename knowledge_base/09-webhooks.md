# Webhooks

Webhooks notify your application when something happens in a store, so you don't have to poll the API. Create subscriptions in **Settings > Developers > Webhooks** or with `POST /v2/webhooks` (requires the `manage_webhooks` scope). Endpoints must use HTTPS.

## Events

| Event | Sent when |
|---|---|
| `order.created` | A new order is placed (including unconfirmed COD orders) |
| `order.paid` | An order's payment is captured |
| `order.fulfilled` | All items in an order are marked as shipped |
| `order.cancelled` | An order is cancelled, including COD auto-cancellation after 48 hours |
| `order.refunded` | A full or partial refund is created |
| `product.created` / `product.updated` / `product.deleted` | Catalogue changes |
| `inventory.low_stock` | A variant reaches its low-stock threshold |
| `customer.created` | A customer account is created |
| `payout.sent` | A NestPay payout is sent to the bank |
| `app.uninstalled` | An app is removed from the store |

## Payload

Every delivery is a `POST` with a JSON body:

```json
{
  "id": "evt_01J9ZQ...",
  "type": "order.paid",
  "created_at": "2026-10-02T09:14:03Z",
  "store_id": "st_4821",
  "data": { "order": { "id": "ord_99312", "total": "7998.00", "currency": "PKR" } }
}
```

Use the event `id` to ignore duplicates: the same event can occasionally be delivered more than once.

## Verifying signatures

Each request includes two headers:

- `X-Nestora-Timestamp`: Unix time when the request was signed
- `X-Nestora-Signature`: hex-encoded HMAC-SHA256 of `timestamp + "." + raw_body`, using your webhook signing secret

Reject requests whose signature does not match, or whose timestamp is more than **5 minutes** old (to block replay attacks). Always compute the HMAC over the raw request body, before parsing the JSON. If signatures never match, check that your framework is not re-serialising the body; this is the most common cause of error NS-6001.

### PHP / Laravel example

```php
$timestamp = $request->header('X-Nestora-Timestamp');
$signature = $request->header('X-Nestora-Signature');
$expected  = hash_hmac('sha256', $timestamp . '.' . $request->getContent(), config('services.nestora.webhook_secret'));

if (! hash_equals($expected, $signature) || abs(time() - (int) $timestamp) > 300) {
    abort(401, 'Invalid Nestora signature');
}
```

### Node.js / Express example

```js
const crypto = require('crypto');

app.post('/webhooks/nestora', express.raw({ type: 'application/json' }), (req, res) => {
  const ts = req.get('X-Nestora-Timestamp');
  const expected = crypto.createHmac('sha256', process.env.NESTORA_WEBHOOK_SECRET)
    .update(`${ts}.${req.body}`).digest('hex');
  const valid = crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(req.get('X-Nestora-Signature')));
  if (!valid || Math.abs(Date.now() / 1000 - Number(ts)) > 300) return res.sendStatus(401);
  res.sendStatus(200); // acknowledge fast, then process the event in a queue
});
```

## Responding and retries

Your endpoint must return a `2xx` status within **10 seconds**. Do slow work in a background job after responding.

Failed deliveries (timeouts, connection errors or non-2xx responses) are retried up to **8 times over about 24 hours**, at these intervals after the first attempt: 1 minute, 5 minutes, 15 minutes, 1 hour, 2 hours, 4 hours, 8 hours and 8 hours.

If an endpoint fails every delivery for 3 consecutive days, Nestora disables the subscription, emails the store owner and returns error NS-6002 for that endpoint in the dashboard. Re-enable it in **Settings > Developers > Webhooks** after fixing the problem; missed events can be re-sent from the delivery log for up to 7 days.

## Testing

Use **Send test event** in the dashboard to deliver a sample payload of any event type. During local development, expose your server with a tunnelling tool and use a test-mode store.
