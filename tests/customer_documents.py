"""Customer document numbers for tests (ownership identity, not broker IDs)."""

CUST_111 = "11111111100"
CUST_222 = "22222222200"
CUST_333 = "33333333300"
CUST_444 = "44444444400"
CUST_SHARED = "99999999900"

# Broker alias -> customer document for matching tests (not derived from broker id).
BY_BROKER: dict[str, str] = {
    "B1": CUST_111,
    "B2": CUST_222,
    "B3": CUST_333,
    "B4": CUST_444,
    "broker-a": CUST_111,
    "broker-b": CUST_222,
    "broker-c": CUST_333,
    "broker1": CUST_111,
    "broker2": CUST_222,
    "brokerB": CUST_222,
    "brokerA": CUST_111,
    "brokerC": CUST_333,
    "buyer": CUST_222,
    "buyer-b": CUST_222,
    "buyer-c": CUST_333,
    "buyer/": CUST_222,
    "seller": CUST_111,
    "seller-a": CUST_111,
    "seller-b": CUST_222,
    "seller1": CUST_111,
    "seller2": CUST_222,
    "secret-seller": CUST_111,
    "secret-buyer": CUST_222,
    "s1": CUST_111,
    "s2": CUST_222,
    "s3": CUST_333,
    "b1": CUST_222,
    "b2": CUST_333,
    "b3": CUST_444,
    "default": CUST_111,
    "smoke-broker": CUST_111,
    "my-broker": CUST_111,
    "curl-broker": CUST_111,
    "qa-broker-a": CUST_111,
    "qa-broker-b": CUST_222,
    "live-a": CUST_111,
    "live-b": CUST_222,
    "live-c": CUST_333,
    "live-d": CUST_444,
    "st-a": CUST_111,
    "st-b": CUST_222,
    "st-c": CUST_333,
    "st-d": CUST_444,
    "st-e": CUST_111,
    "st-f": CUST_222,
    "st-g": CUST_333,
}

for _n in range(1, 12):
    BY_BROKER[f"B{_n}"] = f"{_n:011d}"
for _n in range(1, 11):
    BY_BROKER[f"BROKER-{_n}"] = f"{100 + _n:011d}"
BY_BROKER["BROKER-ALPHA"] = CUST_111
BY_BROKER["BROKER-BETA"] = CUST_222
BY_BROKER["BROKER-C"] = CUST_333
BY_BROKER["buyer1"] = CUST_222


def doc_for(broker_id: str) -> str:
    """Return a fixed customer document for a test broker alias."""
    return BY_BROKER.get(broker_id, CUST_111)
