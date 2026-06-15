from crawlers.moel_qnr_crawler import (
    MoelQnrCrawler
)
from crawlers.moel_faq_crawler import (
    MoelFaqCrawler
)

if __name__ == "__main__":

    MoelQnrCrawler().run()

    MoelFaqCrawler().run()