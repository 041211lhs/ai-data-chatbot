"""data/semiconductor_production.csv(115개월)를 Firestore data 컬렉션에 한 번 올린다.
실행: python seed.py          (이미 있는 날짜는 건너뜀)
      python seed.py --reset  (data 컬렉션을 비우고 다시 올림)"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from services.firestore import DATA, get_db

CSV_PATH = Path(__file__).parent / "data" / "semiconductor_production.csv"


def main():
    db = get_db()
    col = db.collection(DATA)

    if "--reset" in sys.argv:
        for doc in col.stream():
            doc.reference.delete()
        print("data 컬렉션을 비웠다")

    existing = {doc.to_dict()["date"] for doc in col.stream()}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch, added = db.batch(), 0
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"] in existing:
                continue
            batch.set(col.document(), {
                "date": row["date"], "value": float(row["value"]), "memo": row["memo"],
                "created_at": now, "updated_at": now,
            })
            added += 1
    batch.commit()
    print(f"{added}개 추가, 전체 {len(existing) + added}개")


if __name__ == "__main__":
    main()
