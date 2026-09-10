#!/usr/bin/env python3
"""Generate the data file consumed by the raw-data review checklist."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data_raw"
POINTS_DIR = RAW_DIR / "points"
PENDING_DIR = RAW_DIR / "pending"
OUTPUT = RAW_DIR / "raw_data_checklist_data.js"
EXPECTED_NEW_RHYMES = {"咍": 64, "泰": 27, "灰": 66, "肴": 78}
SKIP_TOP_LEVEL = {
    "dialect_evolution_profiles_full.csv",
    "mainlayer_merge.csv",
    "point_template.csv",
    "wenzhou_raw.csv",
    "wuyu_raw.csv",
    "导入模版Template.csv",
    "新增韵部列表.csv",
}
REQUIRED_COLUMNS = [
    "point_id",
    "point_name",
    "subbranch",
    "lat",
    "lon",
    "韵",
    "声组",
    "汉字",
]


def read_point_file(path: Path) -> dict | None:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if fieldnames[:3] != ["point_id", "point_name", "subbranch"]:
            return None
        rows = list(reader)

    if not rows:
        return None

    first = rows[0]
    reading_column = "读音" if "读音" in fieldnames else (
        fieldnames[8] if len(fieldnames) > 8 else None
    )
    rhyme_counts = Counter((row.get("韵") or "").strip() for row in rows)
    reading_count = 0
    original_rows = [
        row for row in rows if (row.get("韵") or "").strip() not in EXPECTED_NEW_RHYMES
    ]
    new_rhyme_rows = [
        row for row in rows if (row.get("韵") or "").strip() in EXPECTED_NEW_RHYMES
    ]
    original_reading_count = 0
    new_rhyme_reading_count = 0
    if reading_column:
        reading_count = sum(
            bool((row.get(reading_column) or "").strip()) for row in rows
        )
        original_reading_count = sum(
            bool((row.get(reading_column) or "").strip()) for row in original_rows
        )
        new_rhyme_reading_count = sum(
            bool((row.get(reading_column) or "").strip()) for row in new_rhyme_rows
        )

    relative_path = path.relative_to(RAW_DIR).as_posix()
    filename_code = path.name.split("_", 1)[0]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    new_rhymes = {
        rhyme: rhyme_counts.get(rhyme, 0) for rhyme in EXPECTED_NEW_RHYMES
    }

    flags = []
    point_id = (first.get("point_id") or "").strip()
    if point_id != filename_code:
        flags.append(f"文件名点号 {filename_code} 与表内点号 {point_id or '空'} 不一致")
    if missing_columns:
        flags.append("缺少字段：" + "、".join(missing_columns))
    if new_rhymes != EXPECTED_NEW_RHYMES:
        detail = "、".join(
            f"{rhyme} {new_rhymes[rhyme]}/{expected}"
            for rhyme, expected in EXPECTED_NEW_RHYMES.items()
            if new_rhymes[rhyme] != expected
        )
        flags.append("新增韵部数量待核对：" + detail)

    return {
        "path": relative_path,
        "id": point_id,
        "name": (first.get("point_name") or "").strip(),
        "subbranch": (first.get("subbranch") or "未标注分片").strip() or "未标注分片",
        "rows": len(rows),
        "readingCount": reading_count,
        "originalRows": len(original_rows),
        "originalReadingCount": original_reading_count,
        "newRhymeRows": len(new_rhyme_rows),
        "newRhymeReadingCount": new_rhyme_reading_count,
        "readingColumn": reading_column or "未找到",
        "newRhymes": new_rhymes,
        "flags": flags,
    }


def discover_files() -> list[dict]:
    top_level = [
        path for path in sorted(RAW_DIR.glob("*.csv"))
        if path.name not in SKIP_TOP_LEVEL
    ]
    paths = (
        sorted(POINTS_DIR.glob("*.csv"))
        + sorted(PENDING_DIR.glob("*.csv"))
        + top_level
    )
    files = []
    for path in paths:
        point = read_point_file(path)
        if point:
            files.append(point)

    by_id: dict[str, list[dict]] = defaultdict(list)
    for point in files:
        by_id[point["id"]].append(point)
    for point_id, matches in by_id.items():
        if point_id and len(matches) > 1:
            paths_text = "、".join(match["path"] for match in matches)
            for match in matches:
                match["flags"].append(f"点号 {point_id} 出现在多个文件：{paths_text}")

    return sorted(
        files,
        key=lambda point: (
            point["subbranch"],
            point["id"],
            point["path"],
        ),
    )


def main() -> None:
    files = discover_files()
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = json.dumps(files, ensure_ascii=False, separators=(",", ":"))
    content = (
        f"window.RAW_DATA_CHECKLIST_FILES = {payload};\n"
        f"window.RAW_DATA_CHECKLIST_GENERATED_AT = {json.dumps(generated_at)};\n"
    )
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(files)} files")


if __name__ == "__main__":
    main()
