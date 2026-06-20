import urllib.request
import urllib.parse
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# We will use the same valid Aadhaar we generated earlier
valid_aadhaar = "900000000018"

base_url = "https://upfr.agristack.gov.in/farmer-registry-api-up-mis/agristack/v1/api"
endpoint = "/farmerRegistryWorkFlowConfiguration/checkApprovalStatusByAadhaar"

params = {
    "aadhaarNumber": valid_aadhaar,
    "enrollmentNumber": ""
}

url = base_url + endpoint + "?" + urllib.parse.urlencode(params)
print(f"Testing GET URL: {url}")

req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://upfr.agristack.gov.in',
    'Referer': 'https://upfr.agristack.gov.in/farmer-registry-up/'
})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        status_code = response.getcode()
        body = response.read().decode('utf-8')
        print(f"Status Code: {status_code}")
        print("Response Body:")
        print(body)
except Exception as e:
    print(f"Error occurred: {e}")
