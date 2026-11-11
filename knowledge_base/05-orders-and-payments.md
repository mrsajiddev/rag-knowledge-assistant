# Orders and payments

## Order statuses

Every order has a payment status and a fulfilment status.

Payment status:
- **Pending**: the customer chose cash on delivery or bank transfer and has not paid yet.
- **Authorised**: a card payment is approved but not yet captured. Authorisations expire after 7 days.
- **Paid**: the payment is captured.
- **Partially refunded** / **Refunded**.
- **Voided**: an authorisation was cancelled before capture.

Fulfilment status:
- **Unfulfilled**, **Partially fulfilled**, **Fulfilled** (shipped), **Delivered**, **Returned**.

An order can be cancelled while it is unfulfilled. Cancelling a paid order refunds the customer automatically if you tick **Refund payment**.

## Payment methods

NestPay supports:
- Visa, Mastercard and UnionPay debit and credit cards, with 3-D Secure
- Mobile wallets available in Pakistan
- Bank transfer (IBFT) with automatic matching using a unique reference per order
- Mada cards and Apple Pay for Saudi Arabia and UAE stores

Card payments that fail show error NS-3001 ("Payment declined by issuer") to the merchant. The customer is asked to try another card; Nestora does not see the exact reason a bank declined a card.

## NestPay payouts

Payouts are sent to the verified bank account in **Settings > Payments > Payouts**.

- **Payout schedule**: daily for Growth, Scale and Enterprise, with funds paid out 2 business days after the payment is captured (T+2). Starter stores are paid weekly, every Tuesday, for payments captured up to the previous Friday.
- **Minimum payout**: PKR 1,000 (or USD 10 / SAR 40 / AED 40). Smaller balances roll over.
- **First payout**: a new merchant's first payout is held for 7 days for a risk review.
- **Currencies**: Pakistan stores are paid in PKR. UAE stores in AED. Saudi Arabian riyal (SAR) payouts launched in release 6.2 for Saudi stores.

If bank account verification fails (for example the account title does not match the business name), payouts stop and error NS-3005 appears in the dashboard. If NestPay places an account under review, payouts are paused with error NS-3002 until the review is finished, normally within 3 business days.

## Cash on delivery (COD)

Cash on delivery is the most popular payment method for Pakistani stores. Nestora reduces fake and abandoned COD orders with **COD verification**:

1. When a COD order is placed, the customer receives a WhatsApp message (or SMS if WhatsApp is unavailable) asking them to confirm.
2. Confirmed orders move to the fulfilment queue.
3. Orders that are not confirmed within **48 hours** are cancelled automatically, and their stock is released.

Merchants can set a maximum COD order value. The platform-wide maximum is **PKR 150,000** per order; larger orders return error NS-4012 and must be paid online.

COD cash collected by couriers booked through Nestora Ship is remitted to the merchant's NestPay balance within **5 business days** after delivery. The remittance report in **Nestora Ship > COD reconciliation** shows each order, the amount collected, courier charges deducted and the payout date.

## Chargebacks

When a customer disputes a card payment, NestPay notifies the merchant by email and in **Payments > Disputes**. The merchant has **7 days** to upload evidence such as a delivery confirmation or a signed receipt. A chargeback fee of PKR 1,500 (USD 15) is charged per dispute and refunded if the merchant wins.

## Taxes and invoices

Nestora calculates sales tax from the tax rates set in **Settings > Taxes**. Order invoices are generated as PDFs automatically and can include the merchant's NTN (Pakistan) or TRN (UAE / Saudi Arabia).
