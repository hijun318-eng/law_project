import requests
from bs4 import BeautifulSoup

case_number = "2011다23149"
url = f"https://casenote.kr/search/?q={case_number}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = "utf-8"

soup = BeautifulSoup(resp.text, "html.parser")

# Print all tags with class or id that contains 'case', 'content', 'detail'
all_divs = soup.find_all("div")
for d in all_divs:
    cls = d.get("class")
    did = d.get("id")
    if cls or did:
        txt = d.text.strip()[:60].replace("\n", " ")
        print(f"div class={cls} id={did} -> {txt}")

print("\n\n=== Strong/b tags ===")
for s in soup.find_all(["strong", "b"]):
    txt = s.text.strip()
    if len(txt) > 2 and len(txt) < 50:
        print(f"  <{s.name}>: {txt}")

print("\n\n=== Large text sections ===")
# Find elements that contain 판시사항
for keyword in ["판시사항", "판결요지", "참조조문", "주 문", "이 유"]:
    el = soup.find(string=lambda t: t and keyword in t)
    if el:
        parent = el.parent
        print(f"'{keyword}' found in <{parent.name}> class={parent.get('class')}")
        # Print next 200 chars
        nxt = ''
        for sib in parent.find_next_siblings():
            nxt += sib.get_text(strip=True) + " "
            if len(nxt) > 200:
                break
        print(f"  Content preview: {nxt[:200]}")
    else:
        print(f"'{keyword}' NOT found")
        
# Check the actual HTML structure around 판시사항
html_lower = resp.text.lower()
idx = html_lower.find("판시사항")
if idx >= 0:
    print(f"\n\n=== HTML around '판시사항' ===")
    print(resp.text[max(0,idx-200):idx+300])
