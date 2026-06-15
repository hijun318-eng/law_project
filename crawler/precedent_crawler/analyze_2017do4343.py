import requests
from bs4 import BeautifulSoup

cn = "2017도4343"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

url = f"https://casenote.kr/%EB%8C%80%EB%B2%95%EC%9B%90/{cn}"
resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = "utf-8"

print(f"URL: {resp.url}")
print(f"Status: {resp.status_code}")
print(f"Length: {len(resp.text)}")

soup = BeautifulSoup(resp.text, "html.parser")

# Check for PRO content
body = soup.body.get_text() if soup.body else ""
if "PRO 회원" in body or "로그인" in body:
    print(">>> PRO 회원 전용 콘텐츠 <<<")

# Check if cn-case-body exists
case_body = soup.select_one("div.cn-case-body")
if case_body:
    print(f"cn-case-body found, length: {len(case_body.get_text(strip=True))}")
    # Check for panels
    panels = case_body.select("div.panel")
    print(f"Panels in cn-case-body: {len(panels)}")
    
    # Check for reason
    reason = case_body.select_one("div.reason")
    print(f"Reason in cn-case-body: {reason is not None}")
    
    # Print all class names in cn-case-body
    for child in case_body.find_all(recursive=False):
        cls = child.get("class", [])
        print(f"  child: <{child.name}> class={cls} text='{child.text[:60].strip()}'")
else:
    print("No cn-case-body found")
    # Print all top-level divs
    for d in soup.find_all("div", recursive=False):
        cls = d.get("class", [])
        did = d.get("id", "")
        t = d.text[:80].strip().replace("\n", " ")
        print(f"  top div class={cls} id={did}: {t}")

# Also check for panel outside cn-case-body
panels = soup.select("div.panel")
print(f"\nTotal panels in page: {len(panels)}")
for p in panels:
    h = p.select_one("div.panel-heading")
    ht = h.text.strip() if h else "(none)"
    print(f"  panel: {ht}")

reason = soup.select_one("div.reason")
print(f"\nTotal reason: {reason is not None}")
if reason:
    print(f"  reason content: {reason.get_text(strip=True)[:200]}")
