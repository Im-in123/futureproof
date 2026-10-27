"""
12 adversarial test cases for the rate-compliance gate.
Each case has a known correct outcome.

Two dimensions:
- rate vs jurisdiction cap
- whether the pipeline can verify the cap
"""

LEASE_TEMPLATE = """RESIDENTIAL LEASE AGREEMENT

This Lease is made as of January 1, 2027, between Landlord and Tenant
for the property located at 123 Main Street, {city}, {state}.

1. TERM. The initial term shall commence on March 14, 2027 and end on
   March 13, 2028.

2. RENT. Tenant agrees to pay monthly rent of {base_rent}. Tenant agrees
   rent shall increase annually on the first anniversary of the
   commencement date by {rate} percent.

3. SECURITY DEPOSIT. Tenant shall pay a security deposit of {base_rent}.

4. MAINTENANCE. Tenant shall be responsible for all repairs under $500.
"""


def _case(name, city, state, jurisdiction, base_rent, rate, expected, category, note):
    return {
        "name": name,
        "text": LEASE_TEMPLATE.format(city=city, state=state,
                                       base_rent=base_rent, rate=rate),
        "jurisdiction": jurisdiction,
        "base_rent": base_rent,
        "rate": rate,
        "expected": expected,       # ACCEPT | REMOVE | NO_EVIDENCE
        "category": category,
        "note": note,
    }


CASES = [
    # ─── California (cap 10%) ───
    _case("ca_safe_3",   "Los Angeles", "California", "California", 2500, 3.0,  "ACCEPT",       "safe",       "3% is well under CA cap"),
    _case("ca_safe_8",   "Oakland",     "California", "California", 3000, 8.0,  "ACCEPT",       "safe",       "8% is under CA cap"),
    _case("ca_edge_10",  "San Diego",   "California", "California", 2200, 10.0, "ACCEPT",       "edge",       "10% is exactly at CA cap"),
    _case("ca_pred_10_5","San Jose",    "California", "California", 2800, 10.5, "REMOVE",       "predatory",  "10.5% exceeds CA cap by 0.5"),
    _case("ca_pred_18",  "Berkeley",    "California", "California", 3500, 18.0, "REMOVE",       "predatory",  "18% is nearly double CA cap"),
    _case("ca_pred_25",  "Pasadena",    "California", "California", 4000, 25.0, "REMOVE",       "predatory",  "25% is egregiously over CA cap"),

    # ─── New York (cap 5%) ───
    _case("ny_safe_4",   "Manhattan",   "New York",   "New York",   4000, 4.0,  "ACCEPT",       "safe",       "4% is under NY cap of 5%"),
    _case("ny_edge_5",   "Brooklyn",    "New York",   "New York",   3200, 5.0,  "ACCEPT",       "edge",       "5% is exactly at NY cap"),
    _case("ny_pred_7",   "Queens",      "New York",   "New York",   2800, 7.0,  "REMOVE",       "predatory",  "7% exceeds NY cap of 5%"),

    # ─── Oregon (cap 10%) ───
    _case("or_safe_9",   "Portland",    "Oregon",     "Oregon",     2400, 9.0,  "ACCEPT",       "safe",       "9% is under OR cap"),
    _case("or_pred_12",  "Eugene",      "Oregon",     "Oregon",     2100, 12.0, "REMOVE",       "predatory",  "12% exceeds OR cap of 10%"),

    # ─── Unknown jurisdiction (should honestly say "cannot determine") ───
    _case("wy_no_cap",   "Cheyenne",    "Wyoming",    "Wyoming",    1800, 15.0, "NO_EVIDENCE",  "unknown",    "WY has no known cap — system should refuse to guess"),
]
