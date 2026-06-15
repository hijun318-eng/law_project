import requests
from bs4 import BeautifulSoup

case_number = "2011다23149"
url = f"https://casenote.kr/search/?q={case_number}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = "utf-8"
soup = BeautifulSoup(resp.text, "html.parser")

# Check reason div
reason = soup.select_one("div.reason")
if reason:
    print("=== div.reason content (first 1000 chars) ===")
    print(reason.get_text(strip=True)[:1000])
    print(f"\n... (total length: {len(reason.get_text(strip=True))})")
    
    # Check for sub-sections like 주문, 이유
    children = reason.find_all(recursive=False)
    print(f"\nDirect children of reason: {len(children)}")
    for c in children:
        print(f"  <{c.name}> class={c.get('class')} text={c.text[:60]}")
else:
    print("div.reason not found!")

# Check panel structure more carefully
panels = soup.select("div.panel")
print(f"\n=== Found {len(panels)} panels ===")
for p in panels:
    heading = p.select_one("div.panel-heading")
    heading_text = heading.text.strip() if heading else "(no heading)"
    
    # Get content div
    content_divs = p.select("div.issue, div.summary, div.reflaws, div.refcases")
    content_text = ""
    for cd in content_divs:
        content_text = cd.text.strip()[:100]
        break
    
    if not content_text:
        # try any div
        all_divs = p.find_all("div", recursive=False)
        for d in all_divs:
            if "panel-heading" not in d.get("class", []):
                content_text = d.text.strip()[:100]
                break
    
    print(f"  Panel heading='{heading_text}' -> content='{content_text}'")

# Check for 주문 and 이유 in the reason div
if reason:
    html = str(reason)
    for kw in ["주 문", "주문", "이 유", "이유"]:
        if kw in html:
            print(f"\n'{kw}' found in reason")
            # Find the tag
            for tag in reason.find_all(string=lambda t: t and kw in t):
                print(f"  in <{tag.parent.name}> class={tag.parent.get('class')}")
