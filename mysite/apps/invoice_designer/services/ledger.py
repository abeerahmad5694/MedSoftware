"""
invoice_designer.services.ledger
----------------------------------
Previous-balance lookup, kept in its own module (separate from
data_builders.py) as requested.

Logic mirrors apps.myledger.api.general_ledger.create_ledger_rows:

    previous_balance = (sum of Gledg DR + Invoice net_total)
                     - (sum of Gledg CR + Purchase net_total)
                     + opening_balance (from Accounts, sign depends on bal_type)

for all entries with date STRICTLY BEFORE `dateent`.

The excluded_acc_codes set lets callers prevent showing previous balances
for walk-in / cash accounts (e.g. 112000001).

Falls back to a clearly-marked zero balance if the real models are not
available or if the acc_code is excluded.
"""

from datetime import date, datetime
from decimal import Decimal

from django.db.models import Sum

# ── safe imports (standalone / test mode if ERP apps aren't installed) ──
try:
    from apps.myledger.models import Gledg
except ImportError:
    Gledg = None

try:
    from apps.sale.models import Invoice
except ImportError:
    Invoice = None

try:
    from apps.purchase.models import Purchase
except ImportError:
    Purchase = None

try:
    from apps.myaccounts.models import Accounts
except ImportError:
    Accounts = None


# --------------------------------------------------------------------
# Accounts whose previous balance is NEVER shown (e.g. walk-in cash).
# Users can extend this via the template configuration field
# "exclude_prev_balance_acc_codes" stored in the template JSON.
# --------------------------------------------------------------------
DEFAULT_EXCLUDED_ACC_CODES: set = {112000001}


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def get_previous_balance(
    bill_no,
    invoice_type: str,
    dateent,
    acc_code=None,
    excluded_acc_codes: set = None,
) -> dict:
    """
    Returns {"previous_balance": <float>, "as_of_date": <iso date str>}.

    Calculation (matches general_ledger.py):
        prev_balance = (Gledg DR + Invoice net_total)
                     - (Gledg CR + Purchase net_total)
                     ± opening_balance from Accounts

    All filtered by `acc_code` and `date < as_of` date.

    Parameters
    ----------
    bill_no   : The invoice bill number (used to look up acc_code if not given).
    invoice_type : document type string (unused in calculation, kept for API compat).
    dateent   : The invoice entry date — balance is summed for dates BEFORE this.
    acc_code  : If already known, skip the Invoice header lookup.
    excluded_acc_codes : Set of int acc_codes to skip. Defaults to DEFAULT_EXCLUDED_ACC_CODES.
    """
    as_of = _as_date(dateent) or date.today()
    fallback = {"previous_balance": 0.00, "as_of_date": as_of.isoformat()}

    if excluded_acc_codes is None:
        excluded_acc_codes = DEFAULT_EXCLUDED_ACC_CODES

    # ── resolve acc_code if not supplied directly ──────────────────────
    if acc_code is None:
        if Invoice is None or bill_no is None:
            return fallback
        try:
            header = Invoice.objects.filter(
                bill_no=bill_no, is_header=True
            ).only("header_acc_code").first()
            if header is None:
                return fallback
            acc_code = getattr(header, "header_acc_code", None)
        except Exception:
            return fallback

    if acc_code is not None:
        try:
            acc_code = int(acc_code)
        except (ValueError, TypeError):
            pass

    if acc_code is None or acc_code in excluded_acc_codes:
        return fallback

    try:
        # ── 1. Gledg DR / CR sums (date < as_of) ─────────────────────
        if Gledg is not None:
            prev_dr_gledg = (
                Gledg.objects.filter(ACC_CODE=acc_code, DATE__lt=as_of, AMT_TYPE="DR")
                .aggregate(total=Sum("AMOUNT"))["total"]
                or Decimal("0.00")
            )
            prev_cr_gledg = (
                Gledg.objects.filter(ACC_CODE=acc_code, DATE__lt=as_of, AMT_TYPE="CR")
                .aggregate(total=Sum("AMOUNT"))["total"]
                or Decimal("0.00")
            )
        else:
            prev_dr_gledg = prev_cr_gledg = Decimal("0.00")

        # ── 2. Invoice debit side (all sales posted to this acc_code) ─
        if Invoice is not None:
            prev_dr_inv = (
                Invoice.objects.filter(
                    header_acc_code=acc_code, date__lt=as_of, is_header=True
                )
                .aggregate(total=Sum("header_net_total"))["total"]
                or Decimal("0.00")
            )
        else:
            prev_dr_inv = Decimal("0.00")

        # ── 3. Purchase credit side ───────────────────────────────────
        if Purchase is not None:
            prev_cr_pur = (
                Purchase.objects.filter(
                    header_acc_code=acc_code, date__lt=as_of, is_header=True
                )
                .aggregate(total=Sum("header_net_total"))["total"]
                or Decimal("0.00")
            )
        else:
            prev_cr_pur = Decimal("0.00")

        running_balance = Decimal(
            str((prev_dr_gledg + prev_dr_inv) - (prev_cr_gledg + prev_cr_pur))
        )

        # ── 4. Opening balance from chart of accounts ─────────────────
        if Accounts is not None:
            try:
                account = Accounts.objects.filter(ACC_CODE=acc_code).only(
                    "OPENING_BALANCE", "BALANCE_TYPE"
                ).first()
                if account:
                    op_bal = Decimal(str(account.OPENING_BALANCE or 0.0))
                    bal_type = (account.BALANCE_TYPE or "").strip().upper()
                    if bal_type == "DR":
                        running_balance += op_bal
                    else:
                        running_balance -= op_bal
            except Exception:
                pass  # Missing opening balance is non-fatal

        return {
            "previous_balance": float(round(running_balance, 2)),
            "as_of_date": as_of.isoformat(),
        }

    except Exception:
        # Never crash the renderer over a ledger failure
        return fallback
