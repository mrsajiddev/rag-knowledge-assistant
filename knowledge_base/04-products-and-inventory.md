# Products and inventory

## Products and variants

A product can have up to **3 options** (for example Size, Colour and Material) and up to **100 variants** in total. Each variant has its own SKU, price, compare-at price, barcode, weight and inventory quantity. SKUs must be unique within a store; trying to reuse a SKU returns error NS-2001.

Product images can be JPG, PNG or WebP, up to 20 MB and up to 4472 × 4472 pixels each. A product can have up to 250 images. Nestora automatically creates resized and WebP versions for fast loading.

## Collections

Collections group products on the storefront. A **manual collection** contains the products you pick. An **automated collection** includes products that match conditions such as tag, vendor, price or product type, and updates itself when products change.

## Importing products with CSV

Go to **Products > Import** and upload a UTF-8 CSV file. A single file can contain up to **50,000 rows**. Larger catalogues must be split into several files. Required columns:

- `handle`: the URL-friendly identifier; rows with the same handle become variants of one product
- `title`
- `sku`
- `price`

Optional columns include `compare_at_price`, `inventory_qty`, `weight_grams`, `barcode`, `vendor`, `product_type`, `tags`, `image_url`, `option1_name`, `option1_value`, `option2_name`, `option2_value`, `option3_name`, `option3_value` and `status` (`active` or `draft`).

If a required column is missing, the import stops with error NS-2101 and nothing is imported. Rows with other problems are skipped, and a downloadable error report lists each skipped row and the reason.

Merchants moving from WooCommerce can use the WooCommerce importer app instead of CSV; it also copies customers and order history.

## Inventory tracking

Turn on **Track quantity** for a variant to have Nestora reduce stock when an order is placed and restore it when an order is cancelled or a return is restocked. When a variant reaches zero you can either hide it or keep selling ("Continue selling when out of stock").

## Low-stock alerts

Nestora emails the store owner and sends an `inventory.low_stock` webhook when a variant's quantity falls to its low-stock threshold. The default threshold is **5 units** and can be changed per variant or in bulk in **Settings > Inventory**.

## Multiple locations

Stores can keep stock in several locations, such as a warehouse and a shop. The number of locations depends on the plan: 1 on Starter, 2 on Growth, 10 on Scale and unlimited on Enterprise. Orders are fulfilled from the location with priority 1 if it has stock; otherwise Nestora picks the next location in priority order. Stock transfers between locations are created in **Inventory > Transfers**.

## Bundles

A bundle sells several products together at one price, for example a "Winter starter kit". Selling a bundle reduces the stock of each component product. Bundles are available on Growth and above and can contain up to 10 components.

## AI product descriptions

Since release 6.1, the product editor has a **Write description** button that drafts a product description from the title, attributes and images, in English, Urdu or Arabic. Merchants get 200 drafts per month on Starter and unlimited drafts on Growth and above. Drafts are never published automatically.
