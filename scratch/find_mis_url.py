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

# Search for misUrl assignments
print("\nSearching for 'misUrl' or 'misURl' assignments:")
for word in ["misUrl", "misURl", "workFlowUrl", "workflowUrl"]:
    idx = 0
    while True:
        idx = js.find(word, idx)
        if idx == -1:
            break
        print(f"  Word: {word} context:")
        print("  ", js[max(0, idx-100):min(len(js), idx+200)])
        idx += len(word)
