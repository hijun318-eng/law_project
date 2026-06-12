import requests


class HttpClient:

    HEADERS = {
        "User-Agent":
            "Mozilla/5.0 Chrome/137.0"
    }

    @classmethod
    def get(cls, url):

        response = requests.get(
            url,
            headers=cls.HEADERS,
            timeout=20
        )

        response.raise_for_status()

        return response