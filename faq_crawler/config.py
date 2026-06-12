from pathlib import Path

BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data" / "qa"

QNR_SAVE_DIR = DATA_DIR / "moel_go_kr_qnrinfo"
FAQ_SAVE_DIR = DATA_DIR / "moel_go_kr_faqView"

METADATA_DIR = BASE_DIR / "metadata"

QNR_SAVE_DIR.mkdir(parents=True, exist_ok=True)
FAQ_SAVE_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)