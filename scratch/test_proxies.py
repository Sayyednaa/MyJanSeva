import urllib.request
import urllib.parse
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

target_url = "https://upfr.agristack.gov.in/farmer-registry-api-up-mis/agristack/v1/api/farmerRegistryWorkFlowConfiguration/checkApprovalStatusByAadhaar?aadhaarNumber=900000000018&enrollmentNumber="
encoded_url = urllib.parse.quote(target_url)

proxies = {
    "CodeTabs": f"https://api.codetabs.com/v1/proxy?quest={encoded_url}",
    "AllOrigins": f"https://api.allorigins.win/get?url={encoded_url}",
    "Cors.sh": f"https://proxy.cors.sh/{target_url}",
    "CorsProxy.io": f"https://corsproxy.io/?{encoded_url}",
    "ThingProxy": f"https://thingproxy.freeboard.io/fetch/{target_url}"
}

for name, url in proxies.items():
    print(f"\nTesting {name} proxy...")
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    })
    
    # If testing cors.sh, it might need header, but let's see
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            print(f"Status Code: {status_code}")
            print(f"Body length: {len(body)}")
            print(f"Snippet: {body[:200]}")
    except Exception as e:
        print(f"Error: {e}")
