from urllib.parse import (
    parse_qs,
    urlparse
)

from bs4 import BeautifulSoup

from core.base_crawler import BaseCrawler
from core.http_client import HttpClient
from core.metadata_manager import MetadataManager
from config import (
    QNR_SAVE_DIR,
    METADATA_DIR
)


class MoelQnrCrawler(BaseCrawler):

    BASE_URL = "https://www.moel.go.kr"

    LIST_URL = (
        "https://www.moel.go.kr/"
        "info/publicdata/qnrinfo/qnrInfoList.do"
    )

    META_FILE = (
        METADATA_DIR /
        "moel_qnr_metadata.json"
    )

    def __init__(self):

        self.metadata = MetadataManager(
            self.META_FILE
        )

    # -------------------------
    # uid
    # -------------------------

    def extract_uid(self, url):

        query = parse_qs(
            urlparse(url).query
        )

        return query["qnr_uid"][0]

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
                f"[QNR] 목록 수집 "
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
            f"[QNR] 총 URL "
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
            "title": "",
            "document_no": "",
            "reply_date": "",
            "body": "",
            "url": url
        }

        for dl in soup.find_all("dl"):

            dt = dl.find("dt")
            dd = dl.find("dd")

            if not dt or not dd:
                continue

            key = dt.get_text(
                strip=True
            )

            value = dd.get_text(
                " ",
                strip=True
            )

            if key == "제목":
                result["title"] = value

            elif key == "문서번호":
                result["document_no"] = value

            elif key == "회시일자":
                result["reply_date"] = value

        textarea = soup.select_one(
            ".b_content textarea"
        )

        if textarea:

            result["body"] = (
                textarea.get_text(
                    "\n",
                    strip=True
                )
            )

        return result

    # -------------------------
    # 저장
    # -------------------------

    def save_markdown(
        self,
        uid,
        data
    ):

        path = (
            QNR_SAVE_DIR /
            f"고용노동부_행정해석_{uid}.md"
        )

        markdown = f"""---
title: "{data['title']}"
document_no: "{data['document_no']}"
reply_date: "{data['reply_date']}"
source: "고용노동부 행정해석"
url: "{data['url']}"
uid: "{uid}"
---

# {data['title']}

## 본문

{data['body']}
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

            uid = self.extract_uid(url)

            if uid in downloaded:

                continue

            try:

                data = (
                    self.parse_detail(url)
                )

                self.save_markdown(
                    uid,
                    data
                )

                downloaded.add(uid)

                new_count += 1

                print(
                    f"[QNR 저장] "
                    f"{uid}"
                )

            except Exception as e:

                print(
                    f"[QNR ERROR] "
                    f"{uid}"
                )

                print(e)

        self.metadata.save(
            downloaded
        )

        print(
            f"[QNR 신규] "
            f"{new_count}건"
        )