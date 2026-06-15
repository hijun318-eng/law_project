import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

failed = ["2017도4343", "89다카2292", "90누2772"]

for cn in failed:
    url = f"https://casenote.kr/search/?q={cn}"
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = "utf-8"
    print(f"{cn} -> Final URL: {resp.url}")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    h1 = soup.select_one("h1")
    if h1:
        print(f"  H1: {h1.text.strip()[:100]}")
    else:
        print("  No H1 found")
        ttl = soup.title
        print(f"  Title: {ttl.text.strip() if ttl else 'None'}")
    
    body = soup.body.get_text() if soup.body else ""
    if "PRO" in body or "회원" in body:
        print("  => PRO 회원 전용 콘텐츠 감지")
    
    # Check if search result page
    if "/search/" in resp.url:
        # Try alternative URL format
        alt_url = f"https://casenote.kr/%EB%8C%80%EB%B2%95%EC%9B%90/{cn}"
        resp2 = requests.get(alt_url, headers=headers, timeout=15)
        resp2.encoding = "utf-8"
        print(f"  Alt URL ({alt_url}) -> Status: {resp2.status_code}")
        if resp2.status_code == 200:
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            h1_2 = soup2.select_one("h1")
            if h1_2:
                print(f"  Alt H1: {h1_2.text.strip()[:100]}")
    
    print()
