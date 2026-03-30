"""
MongoDB 뷰어 — 주요 컬렉션 문서를 간단히 출력한다.

사용법:
    python dbview.py              # 전체 컬렉션 출력
    python dbview.py accounts     # 특정 컬렉션만 출력
"""

import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGODB_DB", "taskrit")
COLLECTIONS = ["accounts", "abilities", "requirements", "tasks"]


def _crop(value: object, max_len: int = 80) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def print_collection(db, name: str) -> None:
    docs = list(db[name].find({}, {"_id": 0}).limit(20))
    print(f"\n[{name}] count={db[name].count_documents({})}")
    if not docs:
        print("  (empty)")
        return

    for idx, doc in enumerate(docs, start=1):
        print(f"  #{idx} { _crop(doc) }")


def main() -> None:
    targets = COLLECTIONS
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg not in COLLECTIONS:
            print(f"Unknown collection: {arg}")
            print(f"Available: {', '.join(COLLECTIONS)}")
            sys.exit(1)
        targets = [arg]

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    print("=" * 70)
    print(f"Taskrit Mongo Viewer - {MONGO_URI}/{MONGO_DB}")
    print("=" * 70)

    for collection in targets:
        print_collection(db, collection)

    client.close()


if __name__ == "__main__":
    main()
