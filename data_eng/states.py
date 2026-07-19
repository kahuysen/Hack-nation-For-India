"""Canonical Indian state and union-territory names shared by data pipelines."""

import re


CANONICAL_STATE_NAMES = (
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)

CANONICAL_STATE_BY_KEY = {name.upper(): name for name in CANONICAL_STATE_NAMES}
CANONICAL_STATE_KEYS = tuple(CANONICAL_STATE_BY_KEY)

STATE_ALIASES = {
    "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU":
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "NCT OF DELHI": "DELHI",
    "NCT DELHI": "DELHI",
    "MAHARASTRA": "MAHARASHTRA",
    "ORISSA": "ODISHA",
    "PONDICHERRY": "PUDUCHERRY",
    "U T OF PUDUCHERRY": "PUDUCHERRY",
    "TAMILNADU": "TAMIL NADU",
    "UTTARANCHAL": "UTTARAKHAND",
    "UTTRANCHAL": "UTTARAKHAND",
}


def canonical_state_name(value: str | None) -> str | None:
    """Return an official display name, or ``None`` for malformed/non-state data."""
    if value is None:
        return None
    normalized = value.upper().replace("&", " AND ")
    key = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", normalized)).strip()
    key = STATE_ALIASES.get(key, key)
    return CANONICAL_STATE_BY_KEY.get(key)
