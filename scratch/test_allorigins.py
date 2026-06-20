import urllib.request
import urllib.parse
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Querying checkApprovalStatusByAadhaar via AllOrigins
target_url = "https://upfr.agristack.gov.in/farmer-registry-api-up-mis/agristack/v1/api/farmerRegistryWorkFlowConfiguration/checkApprovalStatusByAadhaar?aadhaarNumber=900000000018&enrollmentNumber="
encoded_url = urllib.parse.quote(target_url)

allorigins_url = f"https://api.allorigins.win/get?url={encoded_url}"
print(f"Testing AllOrigins proxy: {allorigins_url}")

req = urllib.request.Request(allorigins_url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        status_code = response.getcode()
        body = response.read().decode('utf-8')
        print(f"Status Code: {status_code}")
        # Parse the JSON response from AllOrigins
        res_json = json.loads(body)
        print("AllOrigins response status:", res_json.get("status"))
        # The actual content is in the "contents" field
        contents = res_json.get("contents")
        print("Contents:")
        print(contents)
except Exception as e:
    print(f"Error occurred: {e}")
