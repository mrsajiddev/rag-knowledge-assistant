# SDKs, apps and integrations

## Official SDKs

Nestora maintains official SDKs for PHP and Node.js. Both wrap API v2, handle pagination and rate-limit retries automatically, and include a webhook signature helper.

### PHP and Laravel

Requires PHP 8.1 or newer.

```bash
composer require nestora/nestora-php
```

```php
use Nestora\Client;

$nestora = new Client(apiKey: env('NESTORA_API_KEY'));
$orders  = $nestora->orders->list(['payment_status' => 'paid', 'limit' => 100]);
```

Laravel users get a service provider and facade automatically through package discovery. Publish the config with `php artisan vendor:publish --tag=nestora-config`, then set `NESTORA_API_KEY` and `NESTORA_WEBHOOK_SECRET` in `.env`. The package registers a `nestora.webhook` middleware that verifies signatures for you.

### Node.js

Requires Node.js 18 or newer.

```bash
npm install @nestora/node
```

```js
import { Nestora } from '@nestora/node';

const nestora = new Nestora({ apiKey: process.env.NESTORA_API_KEY });
for await (const product of nestora.products.listAll({ status: 'active' })) {
  console.log(product.title);
}
```

There is no official Python SDK. Python developers can call the REST API directly.

## WordPress and WooCommerce

- **WooCommerce importer** (free app): moves products, variants, images, customers and up to 3 years of order history from a WooCommerce store. Large stores of 20,000+ products usually import in under two hours.
- **Nestora Buy Button for WordPress** (free plugin): embeds Nestora products and a cart in any WordPress site with a shortcode such as `[nestora_product id="prd_123"]`, while checkout and payments run on Nestora.

## App Marketplace

The App Marketplace at https://apps.nestora.example has more than 300 apps for reviews, loyalty, email marketing, accounting exports and more. Apps are installed from **Apps > Browse marketplace**. Each app requests API scopes, which the merchant approves during installation. Paid apps are billed through the Nestora invoice.

### Built-in channels

- **Social catalogue sync**: syncs the product catalogue to social shopping catalogues every hour.
- **Google product feed**: generates a product feed for shopping ads and free listings.
- **WhatsApp Business notifications**: order confirmations, COD verification and shipping updates sent from the merchant's own WhatsApp Business number (Growth and above; Starter uses Nestora's shared number).
- **Accounting export**: daily CSV export of orders, refunds, fees and payouts in a format accepted by common accounting software.

## Building apps

Developers can build public or private apps. Private apps are used by a single store and are created from **Settings > Developers > Private apps**. Public apps must pass review before being listed in the marketplace. Review takes about 10 business days, and Nestora keeps 15% of app revenue (0% on the first USD 10,000 a developer earns each year).
