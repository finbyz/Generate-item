import frappe
import requests
from frappe import _
from frappe.utils import today, add_days, nowdate
from datetime import datetime

API_URL = "https://cdn.moneyconvert.net/api/latest.json"
BASE_CURRENCY = "USD"
RETENTION_DAYS = 7
REQUEST_TIMEOUT = 10  # seconds




def sync_exchange_rates():
    """
    Scheduled hourly task:
    1. Fetch live rates from moneyconvert API
    2. Upsert Currency Exchange records for all active ERPNext currencies
    3. Delete records older than 7 days
    """
    

    try:
        rates = _fetch_rates()
        if not rates:
            return

        active_currencies = _get_active_currencies()
        if not active_currencies:
            return

        success, failed = _upsert_rates(rates, active_currencies)
        _delete_old_records()

    except Exception as e:
        frappe.log_error(
            title="Currency Sync Error",
            message=frappe.get_traceback()
        )



# STEP 1: Fetch Rates from API


def _fetch_rates():
    """Fetch USD-based rates from moneyconvert API."""
    try:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates")
        if not rates or not isinstance(rates, dict):
            frappe.log_error(
                title="Currency Sync - Invalid API Response",
                message=str(data)
            )
            return None

        return rates

    except requests.exceptions.Timeout:
        frappe.log_error(title="Currency Sync - API Timeout", message=f"Timeout hitting {API_URL}")
        return None

    except requests.exceptions.RequestException as e:
        frappe.log_error(title="Currency Sync - API Error", message=str(e))
        return None



# STEP 2: Get Active ERPNext Currencies


def _get_active_currencies():
    """Return list of enabled currencies from ERPNext (excluding USD base)."""
    return frappe.get_all(
        "Currency",
        filters={"enabled": 1, "name": ["!=", BASE_CURRENCY]},
        pluck="name"
    )



# STEP 3: Calculate Cross Rate


def _calculate_rate(rates, from_currency, to_currency):
    """
    Calculate exchange rate between any two currencies using USD as base.
    USD → ANY  : rates[to]
    ANY → USD  : 1 / rates[from]
    ANY → ANY  : rates[to] / rates[from]
    """
    try:
        if from_currency == BASE_CURRENCY:
            return rates.get(to_currency)

        elif to_currency == BASE_CURRENCY:
            from_rate = rates.get(from_currency)
            return (1 / from_rate) if from_rate else None

        else:
            from_rate = rates.get(from_currency)
            to_rate = rates.get(to_currency)
            if from_rate and to_rate:
                return to_rate / from_rate
            return None

    except (ZeroDivisionError, TypeError):
        return None



# STEP 4: Upsert Currency Exchange Records


def _upsert_rates(rates, active_currencies):
    """
    Create or update Currency Exchange records for today.
    Pairs: USD <-> each active currency + cross rates between active currencies.
    Customize the pairs list below as per your business need.
    """
    current_date = today() 
    success = 0
    failed = 0

    # Build pairs: USD ↔ every active currency
    pairs = []
    for currency in active_currencies:
        pairs.append((BASE_CURRENCY, currency))   # USD → INR etc.
        # for inverse conversion
        pairs.append((currency, BASE_CURRENCY))   # INR → USD etc.


    for from_currency, to_currency in pairs:
        try:
            rate = _calculate_rate(rates, from_currency, to_currency)

            if not rate or rate <= 0:
                failed += 1
                continue

            rate = round(rate, 9)

            _upsert_exchange_record(from_currency, to_currency, rate, current_date)
            success += 1

        except Exception as e:
            failed += 1
            frappe.log_error(
                title=f"Currency Sync - Pair Error {from_currency}→{to_currency}",
                message=frappe.get_traceback()
            )

    frappe.db.commit()
    return success, failed





def _upsert_exchange_record(from_currency, to_currency, rate, date):
    """Insert or update a Currency Exchange record for the given date."""
    existing = frappe.db.get_value(
        "Currency Exchange",
        {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "date": date
        },
        "name"
    )

    if existing:
        frappe.db.set_value(
            "Currency Exchange",
            existing,
            {
                "exchange_rate": rate,
                "modified": datetime.now(),
                "modified_by": "Administrator"
            }
        )
    else:
        doc = frappe.get_doc({
            "doctype": "Currency Exchange",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": rate,
            "date": date
        })
        doc.flags.ignore_permissions = True
        doc.insert()


# STEP 5: Delete Records Older Than 7 Days


def _delete_old_records():
    """Hard delete Currency Exchange records older than RETENTION_DAYS."""
    cutoff_date = add_days(today(), -RETENTION_DAYS)

    old_records = frappe.get_all(
        "Currency Exchange",
        filters={"date": ["<", cutoff_date]},
        pluck="name"
    )

    if not old_records:
        return

    for name in old_records:
        frappe.delete_doc(
            "Currency Exchange",
            name,
            ignore_permissions=True,
            force=True
        )

    frappe.db.commit()



