# =============================================================================
# Mock HR data — keyed by Okta user ID.
#
# In a real system these would be fetched from an HR system (Workday, etc.).
# The user IDs here are placeholders; replace with real Okta user IDs from
# your org once you have the XAA flow working end-to-end.
# =============================================================================

EMPLOYEES: dict[str, dict] = {
    "00u1abc": {
        "okta_user_id": "00u1abc",
        "email":         "alice@example.com",
        "first_name":    "Alice",
        "last_name":     "Smith",
        "department":    "Engineering",
        "title":         "Senior Software Engineer",
        "manager_id":    "00u2def",
        "location":      "San Francisco",
        "start_date":    "2021-03-15",
    },
    "00u2def": {
        "okta_user_id": "00u2def",
        "email":         "bob@example.com",
        "first_name":    "Bob",
        "last_name":     "Jones",
        "department":    "Engineering",
        "title":         "Engineering Manager",
        "manager_id":    None,
        "location":      "San Francisco",
        "start_date":    "2019-07-01",
    },
    "00u3ghi": {
        "okta_user_id": "00u3ghi",
        "email":         "carol@example.com",
        "first_name":    "Carol",
        "last_name":     "White",
        "department":    "HR",
        "title":         "HR Business Partner",
        "manager_id":    None,
        "location":      "New York",
        "start_date":    "2020-11-01",
    },
    "00u4jkl": {
        "okta_user_id": "00u4jkl",
        "email":         "dan@example.com",
        "first_name":    "Dan",
        "last_name":     "Brown",
        "department":    "Sales",
        "title":         "Account Executive",
        "manager_id":    "00u5mno",
        "location":      "Chicago",
        "start_date":    "2022-06-20",
    },
    "00u5mno": {
        "okta_user_id": "00u5mno",
        "email":         "eve@example.com",
        "first_name":    "Eve",
        "last_name":     "Davis",
        "department":    "Sales",
        "title":         "Sales Manager",
        "manager_id":    None,
        "location":      "Chicago",
        "start_date":    "2018-02-14",
    },
}

DEPARTMENTS: list[dict] = [
    {"id": "engineering", "name": "Engineering", "head_count": 42},
    {"id": "hr",          "name": "HR",          "head_count": 8},
    {"id": "sales",       "name": "Sales",       "head_count": 23},
    {"id": "product",     "name": "Product",     "head_count": 12},
    {"id": "finance",     "name": "Finance",     "head_count": 7},
]
