import urllib.request
import urllib.parse
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

target_url = "https://upfr.agristack.gov.in/farmer-registry-api-up-mis/agristack/v1/api/farmerRegistryWorkFlowConfiguration/checkApprovalStatusByAadhaar?aadhaarNumber=900000000018&enrollmentNumber="

# corsproxy.io accepts the unencoded or encoded URL appended directly after "?"
url1 = f"https://corsproxy.io/?{target_url}"
url2 = f"https://corsproxy.io/?{urllib.parse.quote(target_url)}"

for i, url in enumerate([url1, url2], 1):
    print(f"\nTesting corsproxy.io format {i}: {url}")
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            print(f"Status Code: {status_code}")
            print(f"Body length: {len(body)}")
            print(f"Snippet: {body[:300]}")
    except Exception as e:
        print(f"Error: {e}")
