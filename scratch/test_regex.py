import re

rows = [
    "1 Babu Jalela 30 / F SELF XXXX-XXXX- 3401",
    "2 Ram Lal 18 / M SON XXXX-XXXX- 4233",
    "3 Pinky 15 / M SON XXXX-XXXX-4 421",
    "4 Scammer Bhai 16 / M HUSBAND'S YOUNGER BROTHER XXXX-XXXX- 5355",
    "5 Aayein 25 / M HUSBAND'S YOUNGER BROTHER XXXX-XXXX- 2314"
]

pattern = re.compile(r"^(\d+)\s+(.+?)\s+(\d+)\s*/\s*([FM])\s+(.+?)\s+([X\d-]+\s*\d+)", re.IGNORECASE)

for r in rows:
    m = pattern.match(r)
    if m:
        print(f"Matched row: {m.groups()}")
    else:
        print(f"FAILED to match: {r}")
