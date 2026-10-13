from decimal import Decimal


def validate_gledg_amount(lines):

    total_dr = Decimal("0")
    total_cr = Decimal("0")
    for line in lines:
        line.amount = int(line.amount)

        if line.amount <= 0:
            raise ValueError(
                "Amount must be greater than zero"
            )

        if line.amtType == "DR":
            total_dr += line.amount

        elif line.amtType == "CR":
            total_cr += line.amount

        else:
            raise ValueError(
                f"Invalid amt_type {line.amtType}"
            )

    if total_dr != total_cr:
        raise ValueError(
            f"Journal not balanced DR={total_dr} CR={total_cr}"
        )