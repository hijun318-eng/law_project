from backend.ocr_contract.config.constants import RULE_CHECKS, MIN_HOURLY_WAGE
from backend.ocr_contract.rules.parsers.wage_parser import (
    parse_hourly_wage,
    parse_monthly_wage,
)

def check_wage(fields: dict):
    violations = []
    warnings = []

    wage_text = fields.get("임금") or ""

    hourly = parse_hourly_wage(wage_text)
    monthly = parse_monthly_wage(wage_text)

    rule = RULE_CHECKS["최저임금"]

    if hourly:
        if hourly < rule["min_hourly_wage"]:
            violations.append({
                "type": "MIN_WAGE_VIOLATION",
                "field": "임금",
                "detail": f"{hourly} < {MIN_HOURLY_WAGE}",
                "law_ref": rule["law_ref"],
            })

    elif monthly:
        hourly_est = int(monthly / 209)
        if hourly_est < MIN_HOURLY_WAGE:
            violations.append({
                "type": "MIN_WAGE_VIOLATION",
                "field": "임금",
                "detail": f"{hourly_est} < {MIN_HOURLY_WAGE}",
                "law_ref": rule["law_ref"],
            })

    elif wage_text.strip():
        warnings.append({
            "type": "WAGE_PARSE_FAIL",
            "field": "임금",
        })

    return violations, warnings