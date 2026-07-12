"""知識ベースローダー+起動時検証。

正本 = ローカル知識ベース db/(全13ファイル)。基準ハッシュは 正本参照.md
(MANIFEST_正本v1.2の写し)から読む。不一致は黙ってフォールバックせず、
strict時は起動失敗、それ以外はdegraded状態とする。
旧版(v1.1、01〜08フォルダのスナップショット)は一切参照しない。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import KnowledgeValidationError

# 構造検証用の必須トップレベルキー(意味の検証ではなく破損検知が目的)
REQUIRED_KEYS: dict[str, list[str]] = {
    "numerology_core.json": ["systems", "reduction", "calculations", "meanings",
                             "compatibility", "default_policy"],
    "zodiac_core.json": ["signs", "elements", "compatibility", "default_policy", "timing"],
    "interpretation_templates.json": ["numbers", "signs", "part_keys", "part_status"],
    "number_zodiac_combinations.json": ["combination_algorithm", "output_contract",
                                        "priority_when_conflict"],
    "horse_expression_templates.json": ["templates", "language_policy", "placeholders"],
    "human_expression_templates.json": ["templates"],
    "temporal_cycles.json": ["cycle_themes", "period_roles", "applicability_matrix",
                             "combination_rules"],
    "sources_master.json": ["sources", "aliases"],
    "status_vocab.json": ["families", "rule"],
    "ephemeris_policy.json": ["required_bodies", "unknown_birth_time_policy",
                              "cusp_determination_spec"],
    "horse_data_policy.json": ["input_minimum", "name_normalization"],
    "verification_plan.json": ["hypotheses", "lock_rule"],
}


@dataclass
class FileCheck:
    name: str
    ok: bool
    expected_size: int | None = None
    actual_size: int | None = None
    expected_sha16: str | None = None
    actual_sha16: str | None = None
    error: str | None = None


@dataclass
class KnowledgeReport:
    status: str = "ok"  # ok | degraded
    version: str = ""
    manifest_path: str = ""
    kb_dir: str = ""
    files: list[FileCheck] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def loaded_file_count(self) -> int:
        return sum(1 for f in self.files if f.ok)


class KnowledgeStore:
    """検証済み知識への読み取り専用アクセス。"""

    def __init__(self, data: dict[str, dict], schema_sql: str, report: KnowledgeReport):
        self._data = data
        self.schema_sql = schema_sql
        self.report = report

    def __getitem__(self, filename: str) -> dict:
        return self._data[filename]

    @property
    def numerology(self) -> dict:
        return self._data["numerology_core.json"]

    @property
    def zodiac(self) -> dict:
        return self._data["zodiac_core.json"]

    @property
    def interpretation(self) -> dict:
        return self._data["interpretation_templates.json"]

    @property
    def combinations(self) -> dict:
        return self._data["number_zodiac_combinations.json"]

    @property
    def horse_templates(self) -> dict:
        return self._data["horse_expression_templates.json"]

    @property
    def human_templates(self) -> dict:
        return self._data["human_expression_templates.json"]

    @property
    def temporal(self) -> dict:
        return self._data["temporal_cycles.json"]

    @property
    def sources_master(self) -> dict:
        return self._data["sources_master.json"]

    @property
    def status_vocab(self) -> dict:
        return self._data["status_vocab.json"]


def parse_manifest(md_path: Path) -> tuple[str, dict[str, tuple[int, str]]]:
    """正本参照.mdからバージョンとハッシュ表を読む。表が正、コードは持たない。"""
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"00_正本_知識ベース_v([\d.]+)_(\d+)", text)
    version = f"v{m.group(1)}_{m.group(2)}" if m else "unknown"
    table: dict[str, tuple[int, str]] = {}
    for row in re.finditer(
        r"\|\s*([\w.]+\.(?:json|sql))\s*\|\s*(\d+)\s*\|\s*([0-9a-f]{16})\s*\|", text
    ):
        table[row.group(1)] = (int(row.group(2)), row.group(3))
    if not table:
        raise KnowledgeValidationError(f"ハッシュ表が読めません: {md_path}")
    return version, table


def _sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _collect_source_ids(obj, acc: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "source_id" and isinstance(v, str):
                acc.add(v)
            elif k in ("source_ids", "source_ids_used") and isinstance(v, list):
                acc.update(x for x in v if isinstance(x, str))
            elif k == "sources" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                acc.update(v)
            else:
                _collect_source_ids(v, acc)
    elif isinstance(obj, list):
        for x in obj:
            _collect_source_ids(x, acc)


def _collect_statuses(obj, acc: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "status" and isinstance(v, str):
                acc.append(v)
            else:
                _collect_statuses(v, acc)
    elif isinstance(obj, list):
        for x in obj:
            _collect_statuses(x, acc)


def load_knowledge(kb_dir: Path, manifest_md: Path) -> KnowledgeStore:
    report = KnowledgeReport(kb_dir=str(kb_dir), manifest_path=str(manifest_md))
    data: dict[str, dict] = {}
    schema_sql = ""

    try:
        version, table = parse_manifest(manifest_md)
        report.version = version
    except Exception as e:  # noqa: BLE001
        report.status = "degraded"
        report.problems.append(f"manifest: {e}")
        return KnowledgeStore({}, "", report)

    # 1-3) 存在・サイズ・SHA-256・JSON構文・必須キー
    for name, (exp_size, exp_sha) in table.items():
        path = kb_dir / name
        fc = FileCheck(name=name, ok=False, expected_size=exp_size, expected_sha16=exp_sha)
        try:
            raw = path.read_bytes()
        except OSError as e:
            fc.error = f"missing: {e}"
            report.files.append(fc)
            report.problems.append(f"{name}: 読めません")
            continue
        fc.actual_size, fc.actual_sha16 = len(raw), _sha16(raw)
        if fc.actual_size != exp_size or fc.actual_sha16 != exp_sha:
            fc.error = "hash/size mismatch(正本と不一致)"
            report.files.append(fc)
            report.problems.append(
                f"{name}: 期待 {exp_size}/{exp_sha} 実際 {fc.actual_size}/{fc.actual_sha16}")
            continue
        if name.endswith(".json"):
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception as e:  # noqa: BLE001
                fc.error = f"json parse: {e}"
                report.files.append(fc)
                report.problems.append(f"{name}: JSON構文エラー")
                continue
            missing = [k for k in REQUIRED_KEYS.get(name, []) if k not in parsed]
            if missing:
                fc.error = f"required keys missing: {missing}"
                report.files.append(fc)
                report.problems.append(f"{name}: 必須キー欠落 {missing}")
                continue
            data[name] = parsed
        else:
            schema_sql = raw.decode("utf-8")
        fc.ok = True
        report.files.append(fc)

    # 4) 出典ID参照整合
    if "sources_master.json" in data:
        sm = data["sources_master.json"]
        valid = set(sm["sources"]) | set(sm["aliases"])
        for name, d in data.items():
            if name == "sources_master.json":
                continue
            used: set[str] = set()
            _collect_source_ids(d, used)
            bad = sorted(used - valid)
            if bad:
                report.problems.append(f"{name}: 未解決の出典ID {bad}")

    # 5) ステータス語彙(正本規則: 括弧注記可・先頭語一致)
    if "status_vocab.json" in data:
        allowed = {s for fam in data["status_vocab.json"]["families"].values() for s in fam}
        for name, d in data.items():
            if name == "status_vocab.json":
                continue
            statuses: list[str] = []
            _collect_statuses(d, statuses)
            for v in statuses:
                for part in re.split(r"[/+]", v):
                    base = re.sub(r"\(.*?\)", "", part).strip()
                    if base and base not in allowed:
                        report.problems.append(f"{name}: 未定義ステータス '{v}'")
                        break

    # 6) day_theme鏡写し契約(正=numerology_core.meanings、temporal_cyclesはミラー)
    if "numerology_core.json" in data and "temporal_cycles.json" in data:
        meanings = data["numerology_core.json"]["meanings"]
        for num, entry in data["temporal_cycles.json"]["cycle_themes"].items():
            if num.startswith("_") or not isinstance(entry, dict):
                continue
            mirror = entry.get("day_theme")
            canon = meanings.get(num, {}).get("day_theme") if isinstance(
                meanings.get(num), dict) else None
            if mirror is not None and mirror != canon:
                report.problems.append(f"temporal_cycles: day_theme不一致 number={num}")

    if report.problems:
        report.status = "degraded"
    return KnowledgeStore(data, schema_sql, report)
