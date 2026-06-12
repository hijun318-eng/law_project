from urllib.parse import (
    parse_qs,
    urlparse
)

from bs4 import BeautifulSoup

from core.base_crawler import BaseCrawler
from core.http_client import HttpClient
from core.metadata_manager import MetadataManager
from config import (
    FAQ_SAVE_DIR,
    METADATA_DIR
)


class MoelFaqCrawler(BaseCrawler):

    BASE_URL = "https://moel.go.kr"

    LIST_URL = (
        "https://moel.go.kr/"
        "faq/faqList.do"
    )

    META_FILE = (
        METADATA_DIR /
        "moel_faq_metadata.json"
    )

    def __init__(self):

        self.metadata = MetadataManager(
            self.META_FILE
        )

    # -------------------------
    # seq 추출
    # -------------------------

    def extract_seq(self, url):

        query = parse_qs(
            urlparse(url).query
        )

        return query["seqRepeat"][0]

    # -------------------------
    # 목록
    # -------------------------

    def collect_urls(self):

        urls = []

        page = 1

        while True:

            url = (
                f"{self.LIST_URL}"
                f"?pageIndex={page}"
            )

            print(
                f"[FAQ] 목록 수집 "
                f"{page}페이지"
            )

            soup = BeautifulSoup(
                HttpClient.get(url).text,
                "html.parser"
            )

            links = soup.select(
                "table.tstyle_list "
                "tbody tr td.txt_left a"
            )

            if not links:
                break

            for link in links:

                href = link.get("href")

                if not href:
                    continue

                if href.startswith("/"):

                    href = (
                        self.BASE_URL +
                        href
                    )

                urls.append(href)

            page += 1

        print(
            f"[FAQ] 총 URL "
            f"{len(urls)}개"
        )

        return urls

    # -------------------------
    # 상세
    # -------------------------

    def parse_detail(self, url):

        soup = BeautifulSoup(
            HttpClient.get(url).text,
            "html.parser"
        )

        result = {
            "category": "",
            "question": "",
            "answer": "",
            "url": url
        }

        info = soup.select_one(
            "div.b_info"
        )

        if not info:
            return result

        for dl in info.find_all("dl"):

            dt = dl.find("dt")
            dd = dl.find("dd")

            if not dt or not dd:
                continue

            key = dt.get_text(
                strip=True
            )

            value = dd.get_text(
                "\n",
                strip=True
            )

            if key == "카테고리":
                result["category"] = value

            elif key == "질의":
                result["question"] = value

            elif key == "답변":
                result["answer"] = value

        return result

    # -------------------------
    # 저장
    # -------------------------

    def save_markdown(
        self,
        seq,
        data
    ):

        path = (
            FAQ_SAVE_DIR /
            f"고용노동부_FAQ_{seq}.md"
        )

        markdown = f"""---
category: "{data['category']}"
source: "고용노동부 FAQ"
url: "{data['url']}"
seq: "{seq}"
---

# {data['question']}

## 카테고리

{data['category']}

## 답변

{data['answer']}
"""

        path.write_text(
            markdown,
            encoding="utf-8"
        )

    # -------------------------
    # 실행
    # -------------------------

    def run(self):

        downloaded = (
            self.metadata.load()
        )

        urls = self.collect_urls()

        new_count = 0

        for url in urls:

            seq = self.extract_seq(url)

            if seq in downloaded:

                continue

            try:

                data = (
                    self.parse_detail(url)
                )

                self.save_markdown(
                    seq,
                    data
                )

                downloaded.add(seq)

                new_count += 1

                print(
                    f"[FAQ 저장] "
                    f"{seq}"
                )

            except Exception as e:

                print(
                    f"[FAQ ERROR] "
                    f"{seq}"
                )

                print(e)

        self.metadata.save(
            downloaded
        )

        print(
            f"[FAQ 신규] "
            f"{new_count}건"
        )