import urllib.request
import re
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://upfr.agristack.gov.in/farmer-registry-up/"

# List of chunks from runtime
chunks = {
    92:"197f19067aaad20ea43e",93:"ae3c588ed2430dfc607f",403:"9b57c137dfbfe141c68d",565:"808be5071ad3d270c29c",
    864:"6d62322fd9d1ba576a6d",1465:"83b9fdacf97df391b89e",1669:"7b8841e777154b77439e",2279:"f1ac35cf636298946e62",
    2565:"d05206f71124e46ca88a",2907:"9a86af2ac25b7c57c59d",3175:"3ed630abc3e87c2604ed",3362:"a1fceb227a91316d33b9",
    3443:"a8b645edfe56c020072c",3774:"0851acf98fccdac41644",3980:"97fc68b9b95c4074c393",4141:"e253dfcf7360cde3ed8c",
    4279:"bd557f34f67327f752d0",4429:"f1e355f03ee95004359d",4457:"dcd8cdb53eba777113da",4662:"65f59f678c77e9105866",
    4763:"8659946c3a806f9586d8",4919:"d02ff878aa2dcabcc0ac",4983:"58b540cef5a7832b97de",5033:"ff0f89b87dcccacbfdf0",
    5081:"08b4d50b828f9788e8da",5112:"4398613477abe138ff63",5396:"e27a1185388005dc7123",5524:"1a54f007a72ecc56d867",
    5671:"f6aac852ab34403ace4e",5848:"6ae3cb050e6aa42ed59d",6517:"66b3126fd2377a2f365f",6626:"bb09c1718aff403f044f",
    6662:"692d87051d26dd219e35",6747:"73065f9656b094f02a78",6806:"94dfbb1ab8a6272db2b0",6919:"42794edf8910978fe494",
    7024:"abd59c3447afb3a7a9a9",7136:"321bd506213aefcc0e9b",7418:"c2e29726d13c0ab949dc",7497:"3e783297b9fd8fa69171",
    7780:"9965d717853e3008324d",7793:"b4b2ed0ec9b42bbf8671",7938:"7d11e2c1bd212b50b737",8075:"674e6820659de24919ff",
    8090:"1d80b6c1a9e0fb90b47d",8487:"887abd948c41ceb67e75",8592:"895379f2bb8c475c16c0",8602:"60ebac2014f910c75ac3",
    8616:"f83f6d20555f25c3d835",8697:"42345080f9dcf19dc2fa",8699:"b7081a90b8ab130b55c4",8970:"3246ff774d33c4563d14",
    8978:"c3dad5c4ddf44d3f2182",9225:"86e582ac22a976ea7a9c",9627:"915b46ab674183d1f2d9",9725:"7516216aaf10743bb514",
    9795:"3d03ac2b8d981a036dba"
}

print(f"Scanning {len(chunks)} chunks...")

for cid, chash in chunks.items():
    chunk_name = f"{cid}.{chash}.js"
    chunk_url = base_url + chunk_name
    try:
        req = urllib.request.Request(chunk_url, headers={'User-Agent': 'Mozilla/5.0'})
        js = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')
        
        # Search for checkEnrolmentStatus or routing
        if "checkEnrolmentStatus" in js or "check-enrolment" in js or "checkEnrolment" in js:
            print(f"\nFOUND keyword in {chunk_name}!")
            
            # Find snippets
            for kw in ["checkEnrolmentStatus", "check-enrolment", "checkEnrolment"]:
                idx = js.find(kw)
                if idx != -1:
                    print(f"  Keyword '{kw}' context:")
                    print("  ", js[max(0, idx-200):min(len(js), idx+600)])
                    
        # Search for endpoints making a post/get request with "status" or "enroll" or "enrol"
        matches = re.findall(r'httpClient\.(?:post|get)\([^\)]+\)', js)
        for m in matches:
            if "status" in m.lower() or "enrol" in m.lower() or "farmer" in m.lower():
                print(f"  Possible HTTP call in {chunk_name}: {m}")
    except Exception as e:
        pass
print("Scan finished.")
