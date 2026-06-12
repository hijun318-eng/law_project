from preprocess_qna import run_qna
from preprocess_case import run_case
from preprocess_law import run_law


CONFIG = {
    "qna": {
        "input_dir": "../data/raw/pdf",
        "output_dir": "../data/process/qna"
    },
    "case": {
        "input_dir": "../data/raw/case",
        "output_dir": "../data/process/case"
    },
    "law": {
        "input_dir": "../data/raw/law",
        "output_dir": "../data/process/law"
    }
}


if __name__ == "__main__":
    run_qna(**CONFIG["qna"])
    run_case(**CONFIG["case"])
    run_law(**CONFIG["law"])