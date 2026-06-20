import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://upfr.agristack.gov.in/farmer-registry-up/"
chunk_name = "4279.bd557f34f67327f752d0.js"
chunk_url = base_url + chunk_name

print(f"Downloading {chunk_url}...")
req = urllib.request.Request(chunk_url, headers={'User-Agent': 'Mozilla/5.0'})
js = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')

# Search for checkApprovalStatusByAadhaar
kw = "checkApprovalStatusByAadhaar"
idx = 0
while True:
    idx = js.find(kw, idx)
    if idx == -1:
        break
    print(f"\nFound keyword '{kw}' at index {idx}:")
    print(js[max(0, idx-500):min(len(js), idx+500)])
    idx += len(kw)

# Search for checkApprovalStatusForUFR
kw2 = "checkApprovalStatusForUFR"
idx2 = 0
while True:
    idx2 = js.find(kw2, idx2)
    if idx2 == -1:
        break
    print(f"\nFound keyword '{kw2}' at index {idx2}:")
    print(js[max(0, idx2-500):min(len(js), idx2+500)])
    idx2 += len(kw2)
