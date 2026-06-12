from abc import ABC, abstractmethod


class BaseCrawler(ABC):

    @abstractmethod
    def collect_urls(self):
        pass

    @abstractmethod
    def parse_detail(self, url):
        pass

    @abstractmethod
    def run(self):
        pass