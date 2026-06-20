import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://upfr.agristack.gov.in/farmer-registry-up/"
chunk_name = "4279.bd557f34f67327f752d0.js"
chunk_url = base_url + chunk_name

print("Downloading chunk...")
req = urllib.request.Request(chunk_url, headers={'User-Agent': 'Mozilla/5.0'})
js = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

# Search for the first occurrence of workFlowUrl
first_idx = js.find("workFlowUrl")
print(f"First occurrence of workFlowUrl: {first_idx}")
if first_idx != -1:
    print(js[max(0, first_idx-500):first_idx+500])

# Also search for "misUrl =" or "misUrl:" or "misUrl" in general
first_mis = js.find("misUrl")
print(f"\nFirst occurrence of misUrl: {first_mis}")
if first_mis != -1:
    print(js[max(0, first_mis-500):first_mis+500])
