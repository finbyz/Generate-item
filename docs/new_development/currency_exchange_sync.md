# Currency Exchange Synchronization

## Purpose

The scheduled service maintains current ERPNext Currency Exchange records using USD-based rates from an external MoneyConvert API.

Primary implementation:

- `generate_item/utils/currency_exchange.py`
- scheduler registration in `generate_item/hooks.py`

## Schedule

```text
0 */4 * * *
```

The task runs every four hours.

## Processing

1. Fetch USD-based external rates.
2. Read enabled ERPNext currencies.
3. Calculate USD-to-currency, currency-to-USD, and configured cross rates.
4. Insert or update current-date Currency Exchange records.
5. Delete exchange records older than seven days.

## Rate calculation

```text
USD -> target: target USD-base rate
source -> USD: 1 / source USD-base rate
source -> target: target rate / source rate
```

## Operational requirements

- outbound network access;
- available external API;
- valid currency codes;
- scheduler and workers enabled;
- permission to create/update Currency Exchange.

Failures should be monitored in scheduler logs and Error Log. Exchange-rate accuracy depends on the external provider.

