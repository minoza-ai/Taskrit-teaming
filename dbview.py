"""
DB 뷰어 — taskrit.db의 모든 테이블을 표 형식으로 출력한다.

사용법:
    python db_viewer.py          # 전체 테이블 출력
    python db_viewer.py accounts # 특정 테이블만 출력
"""

import sqlite3
import sys

DB_PATH = "taskrit.db"

TABLES = ["accounts", "abilities", "requirements", "tasks"]


def print_table(cursor: sqlite3.Cursor, table_name: str) -> None:
    """테이블 데이터를 표 형태로 출력한다."""
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
    except sqlite3.OperationalError as e:
        print(f"  ⚠ 테이블을 읽을 수 없습니다: {e}\n")
        return

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    if not rows:
        print(f"  (비어 있음 — 0 rows)\n")
        return

    # 컬럼별 최대 너비 계산 (헤더 포함)
    col_widths = []
    for i, col in enumerate(columns):
        max_w = len(col)
        for row in rows:
            cell = str(row[i]) if row[i] is not None else "NULL"
            # 너무 긴 셀은 잘라서 표시
            if len(cell) > 60:
                cell = cell[:57] + "..."
            max_w = max(max_w, len(cell))
        col_widths.append(max_w)

    # 헤더 출력
    header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
    separator = "-+-".join("-" * w for w in col_widths)
    print(f"  {header}")
    print(f"  {separator}")

    # 데이터 행 출력
    for row in rows:
        cells = []
        for i, val in enumerate(row):
            cell = str(val) if val is not None else "NULL"
            if len(cell) > 60:
                cell = cell[:57] + "..."
            cells.append(cell.ljust(col_widths[i]))
        print(f"  {' | '.join(cells)}")

    print(f"\n  → {len(rows)} row(s)\n")


def main() -> None:
    target_tables = TABLES

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in TABLES:
            target_tables = [arg]
        else:
            print(f"알 수 없는 테이블: {arg}")
            print(f"사용 가능: {', '.join(TABLES)}")
            sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 70)
    print(f"  Taskrit DB Viewer - {DB_PATH}")
    print("=" * 70)

    for table in target_tables:
        print(f"\n┌─ {table.upper()} ─")
        print_table(cursor, table)

    conn.close()


if __name__ == "__main__":
    main()
