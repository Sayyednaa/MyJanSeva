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

# Search for components calling checkApprovalStatus or checkEnrolmentStatus
print("\nSearching checkApprovalStatus calls:")
idx = 0
while True:
    idx = js.find("checkApprovalStatus", idx)
    if idx == -1:
        break
    print(f"  Match at {idx}:")
    print("  ", js[max(0, idx-300):min(len(js), idx+500)])
    idx += len("checkApprovalStatus")

print("\nSearching checkEnrolmentStatus calls:")
idx = 0
while True:
    idx = js.find("checkEnrolmentStatus", idx)
    if idx == -1:
        break
    print(f"  Match at {idx}:")
    print("  ", js[max(0, idx-300):min(len(js), idx+500)])
    idx += len("checkEnrolmentStatus")
