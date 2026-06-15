import os

cases_dir = r"C:\Users\Playdata\Documents\law_crawler\cases"
for f in sorted(os.listdir(cases_dir)):
    path = os.path.join(cases_dir, f)
    size = os.path.getsize(path)
    with open(path, "r", encoding="utf-8") as fh:
        first_line = fh.readline().strip()[:80]
    print(f"{size:>6}B  {f}: {first_line}")
