# Shipping and delivery (Nestora Ship)

Nestora Ship lets merchants book couriers, print labels and track deliveries without leaving the dashboard. It is included on every plan; merchants pay only the courier charges, which are deducted from their NestPay balance.

## Partner couriers

| Courier | Countries | Strengths |
|---|---|---|
| SwiftRoute Express | Pakistan | Next-day delivery between major cities, COD |
| Indus Couriers | Pakistan | Widest coverage, including smaller towns, COD |
| BlueCamel Logistics | UAE, Saudi Arabia | Same-day delivery in Dubai and Riyadh |

Merchants can also mark orders as fulfilled with any other courier and paste in a tracking number manually.

## Rates

Courier rates are calculated by weight in 0.5 kg slabs and by destination zone (same city, same province, other province). Volumetric weight (length × width × height in cm ÷ 5000) is used when it is higher than the actual weight. The rate card for each courier is in **Nestora Ship > Rates**. Scale and Enterprise merchants receive discounted rates of about 10%.

## Booking and pickups

1. Open an unfulfilled order and choose **Book courier**.
2. Pick the courier and service, and confirm the package weight and dimensions.
3. Print the label (A4 or 4 × 6 inch thermal format) and attach it to the parcel.

Bookings made before **2:00 PM local time** on a working day are picked up the same day. Bookings made after the cut-off are picked up the next working day; trying to request a same-day pickup after the cut-off returns error NS-4002.

If the destination is not served by the chosen courier, booking fails with error NS-4001 ("Area not serviceable"). Try a different courier; Indus Couriers has the widest coverage in Pakistan.

## Tracking

Tracking updates are pulled from couriers every 30 minutes. Customers receive email and WhatsApp updates when the order is shipped, out for delivery and delivered. The tracking page uses the store's branding.

## Failed deliveries and returns to origin

A courier makes up to **3 delivery attempts**. If all attempts fail, or the customer refuses a COD parcel, the parcel is returned to the merchant ("return to origin", RTO). The forward shipping charge still applies and an RTO charge of 50% of the forward charge is added. RTO parcels usually arrive back within 7 to 10 days.

To reduce RTOs, keep COD verification turned on, and consider blocking COD for customers with two or more refused parcels (**Settings > Payments > Cash on delivery > Risk rules**).

## International shipping

International shipping is not available through Nestora Ship. Merchants can still sell internationally and ship with their own courier, adding customs details manually.
