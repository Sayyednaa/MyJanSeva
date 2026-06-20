# Verhoeff algorithm implementation
d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

p_standard = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 5, 8, 2]
]

inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def generate_verhoeff(num_str):
    c = 0
    for i, digit in enumerate(reversed(num_str)):
        c = d[c][p_standard[(i + 1) % 8][int(digit)]]
    return str(inv[c])

# Try to find a valid 12-digit Aadhaar number
base = "90000000001"
check_digit = generate_verhoeff(base)
valid_aadhaar = base + check_digit

import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://upfr.agristack.gov.in/farmer-registry-api-up/agristack/v1/api"
endpoint = "/farmerRegistryWorkFlowConfiguration/checkApprovalStatus"
url = base_url + endpoint

body = {
    "isCheckStatusAgainstEnrolmentNumber": False,
    "isCheckStatusAgainstCentralId": False,
    "aadhaarNumber": valid_aadhaar
}

data = json.dumps(body).encode('utf-8')
print(f"Testing POST URL: {url}")
print(f"Using Aadhaar: {valid_aadhaar}")

req = urllib.request.Request(url, data=data, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Origin': 'https://upfr.agristack.gov.in',
    'Referer': 'https://upfr.agristack.gov.in/farmer-registry-up/'
})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        print("Response:", response.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
