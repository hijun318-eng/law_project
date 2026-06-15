import requests
from bs4 import BeautifulSoup

case_number = "2011다23149"
url = f"https://casenote.kr/search/?q={case_number}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = "utf-8"
print(f"Final URL: {resp.url}")
print(f"Status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")

h2s = soup.find_all("h2")
for h2 in h2s:
    txt = h2.text.strip()[:100]
    print(f"H2: {txt}")

# Check main content area
for sel in [".container", ".content", "#content", "main", "article", ".case-detail", "#case-detail", "div.col", ".col"]:
    el = soup.select_one(sel)
    if el:
        print(f"Found '{sel}': tag={el.name}, class={el.get('class')}, id={el.get('id')}")
        break
else:
    print("No standard container found")

# Find the content area by looking for h1 that contains 판결
h1 = soup.find("h1")
if h1:
    print(f"\nH1 text: {h1.text.strip()[:150]}")
    parent = h1.parent
    print(f"H1 parent: tag={parent.name}, class={parent.get('class')}, id={parent.get('id')}")

# Check how 판시사항 section is structured
sections = soup.find_all(["h2", "h3", "h4"])
print("\n--- ALL sections found ---")
for s in sections:
    tag = s.name
    txt = s.text.strip()[:60]
    # get next siblings
    nxt = s.find_next_sibling()
    nxt_preview = nxt.text.strip()[:80] if nxt and nxt.text else "(none)"
    print(f"  {tag}: {txt}")
