import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# We will use corsproxy.io as the prefix
proxy_prefix = "https://corsproxy.io/?"
target_url = "https://upfr.agristack.gov.in/farmer-registry-api-up/agristack/v1/api/farmerRegistryWorkFlowConfiguration/checkApprovalStatus"
url = proxy_prefix + target_url

body = {
    "isCheckStatusAgainstEnrolmentNumber": False,
    "isCheckStatusAgainstCentralId": False,
    "aadhaarNumber": "900000000018"
}

data = json.dumps(body).encode('utf-8')
print(f"Testing POST via CORS proxy: {url}")

req = urllib.request.Request(url, data=data, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Origin': 'https://upfr.agristack.gov.in',
    'Referer': 'https://upfr.agristack.gov.in/farmer-registry-up/'
})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        status_code = response.getcode()
        body_res = response.read().decode('utf-8')
        print(f"Status Code: {status_code}")
        print(f"Response Body: {body_res}")
except Exception as e:
    print(f"Error occurred: {e}")
