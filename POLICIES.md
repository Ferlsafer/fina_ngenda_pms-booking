# Business & Security Policies

## Financial records (soft delete)

- Invoices, payments, journal entries, and journal lines must not be hard-deleted.
- These models have a `deleted_at` (nullable datetime) column. Set `deleted_at` to the current time to soft-delete; leave `None` for active records.
- All reads (dashboard revenue, accounting list, payment totals) exclude rows where `deleted_at` is not null.

## Overpayment policy

**Policy: Overpayment is allowed.**

- When recording a payment, the total paid on an invoice may exceed the invoice total.
- Invoice status is set to **Paid** when the sum of payments is greater than or equal to the invoice total; otherwise it is set to **PartiallyPaid**.
- No cap is applied to the payment amount; excess is accepted (e.g. tips, rounding, or manual adjustment).
- To enforce strict no-overpayment behaviour, the payment route would need to cap the accepted amount at `invoice.total - paid_total` and reject the form with an error.
