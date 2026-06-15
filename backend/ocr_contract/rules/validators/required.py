from backend.ocr_contract.config.constants import REQUIRED_FIELDS
from backend.ocr_contract.rules.core.blank_checker import is_blank

def check_required(fields: dict):
    missing = {}

    for field, law in REQUIRED_FIELDS.items():
        if is_blank(fields.get(field)):
            missing[field] = law

    return missing