import argparse
import sys
from backend.ocr_contract.pipeline import analyze_contract, print_result
from backend.ocr_contract.rules.validators.contract_gate import NotAContractError

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    args = parser.parse_args()

    try:
        result = analyze_contract(args.image)
        print_result(result)
 
    except NotAContractError as e:
        print(f"\n❌ 업로드된 파일이 근로계약서가 아닙니다.")
        print(f"   사유: {e.reason}")
        sys.exit(1)