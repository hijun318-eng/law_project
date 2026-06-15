import json
from pathlib import Path


class MetadataManager:

    def __init__(self, path):

        self.path = Path(path)

        if not self.path.exists():

            self.save(set())

    def load(self):

        with open(
            self.path,
            encoding="utf-8"
        ) as f:

            return set(
                json.load(f)
            )

    def save(self, ids):

        with open(
            self.path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                list(ids),
                f,
                ensure_ascii=False,
                indent=4
            )