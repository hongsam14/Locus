"""V3: a demo's card text and translation files in the manifest, the name = world.id
check, and reading the entries at run time (FD BLM § 5·6, BR-V3-06·08~12·18·19,
TP-V3-3·4·5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locus.world.demo import WORLDS_DIR, DemoWorlds
from locus.world.worldfile import remapped_id, translatable_texts
from locus.world.worldfile.schema import WorldFile

PACKAGED = json.loads((WORLDS_DIR / "emberleaf.world.json").read_text(encoding="utf-8"))


def _texts() -> dict:
    return translatable_texts(WorldFile.parse(PACKAGED))


def _full(lang: str = "ko", world_id: str | None = None) -> dict:
    """A translation file covering every text of the packaged World File."""
    return {
        "format": "locus.translations",
        "version": 1,
        "lang": lang,
        "world_id": world_id or PACKAGED["world"]["id"],
        "entries": [
            {"kind": k, "id": i, "field": f, "source": src, "text": f"번역 {i}.{f}"}
            for (k, i, f), src in _texts().items()
        ],
    }


def _folder(tmp_path: Path, *, translation: dict | str | None, **entry) -> Path:
    name = PACKAGED["world"]["id"]
    (tmp_path / f"{name}.world.json").write_text(json.dumps(PACKAGED), encoding="utf-8")
    item = {
        "name": name,
        "title": "Isle",
        "file": f"{name}.world.json",
        "start_region_id": PACKAGED["regions"][0]["id"],
        "translations": {"ko": f"{name}.ko.json"},
        **entry,
    }
    if translation is not None:
        body = translation if isinstance(translation, str) else json.dumps(translation)
        (tmp_path / f"{name}.ko.json").write_text(body, encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps([item]), encoding="utf-8")
    return tmp_path


def _start_region() -> str:
    # a region with a passable connection, so the entry passes the start check
    for c in PACKAGED["connections"]:
        if c["kind"] != "blocked" and c["weight"] > 0:
            return c["source_region_id"]
    raise AssertionError("no passable connection")


@pytest.fixture
def folder(tmp_path: Path):
    def make(translation, **entry) -> DemoWorlds:
        entry.setdefault("start_region_id", _start_region())
        return DemoWorlds(worlds_dir=_folder(tmp_path, translation=translation, **entry))

    return make


# --- the check (TP-V3-4) ----------------------------------------------------------- #
def test_a_complete_file_is_no_problem(folder) -> None:
    demos = folder(_full())
    assert demos.problems == [] and len(demos.list()) == 1


def _problems_of(folder, translation, **entry) -> str:
    demos = folder(translation, **entry)
    assert len(demos.list()) == 1  # BR-V3-10: the demo stays
    assert demos.problems, "expected a problem"
    text = " | ".join(demos.problems)
    assert text.startswith(f"{PACKAGED['world']['id']}: translations ko")  # BR-V3-09
    return text


def test_a_path_outside_the_folder(folder) -> None:  # (a)
    assert "outside the demo folder" in _problems_of(
        folder, _full(), translations={"ko": "../elsewhere.json"}
    )


def test_an_unreadable_or_foreign_file(folder) -> None:  # (b)
    assert "unreadable" in _problems_of(folder, "{not json")
    assert "not a translation file" in _problems_of(folder, {"format": "x"})
    bad = _full()
    bad["entries"][0]["field"] = "role"  # a region has no role
    assert "invalid translation file" in _problems_of(folder, bad)


def test_lang_and_world_must_match(folder) -> None:  # (c) (d)
    assert "the file says lang 'ja'" in _problems_of(folder, _full(lang="ja"))
    assert "made for world 'other'" in _problems_of(folder, _full(world_id="other"))


def test_duplicates_unknown_keys_and_stale_sources(folder) -> None:  # (e) (f) (g)
    data = _full()
    first = dict(data["entries"][0])
    data["entries"].append(first)
    data["entries"].append({**first, "id": "region-nowhere"})
    data["entries"][1] = {**data["entries"][1], "source": "An older text"}
    text = _problems_of(folder, data)
    assert f"duplicate {first['kind']} {first['id']}.{first['field']}" in text
    assert f"unknown {first['kind']} region-nowhere.{first['field']}" in text
    assert "stale" in text and "'An older text' ≠ world" in text


def test_untranslated_texts_are_counted(folder) -> None:  # (h)
    data = _full()
    data["entries"] = data["entries"][:-7]
    assert "7 texts untranslated" in _problems_of(folder, data)
    assert "and 2 more" in _problems_of(folder, data)  # five named, the rest counted


def test_the_name_must_be_the_world_id(folder) -> None:  # FR-C11, BR-V3-11
    demos = folder(_full(), name="isle")
    assert demos.list() == []
    assert "is world" in demos.problems[0] and "the names must match" in demos.problems[0]


@pytest.mark.parametrize("key", ["en", "kor", "KO"])
def test_a_bad_language_key_is_a_manifest_error(folder, key: str) -> None:  # BR-V3-12, R-06
    demos = folder(_full(), translations={key: "x.json"})
    assert demos.list() == [] and "invalid field" in demos.problems[0]
    demos = folder(_full(), i18n={key: {"title": "섬"}})
    assert demos.list() == []


def test_card_text_is_capped_like_the_english(folder) -> None:  # BR-V3-12
    assert folder(_full(), i18n={"ko": {"title": "섬" * 61}}).list() == []
    demos = folder(_full(), i18n={"ko": {"title": "엠버리프 섬", "credits": "독창적인 세계"}})
    card = demos.card(PACKAGED["world"]["id"], "ko")
    assert card is not None and card.title == "엠버리프 섬" and card.description is None
    assert demos.card(PACKAGED["world"]["id"], "ja") is None


# --- run time (TP-V3-5, TP-V3-3) ------------------------------------------------------ #
def test_a_broken_file_reads_as_no_entries(folder) -> None:  # BR-V3-10
    demos = folder("{not json")
    name = PACKAGED["world"]["id"]
    assert demos.translations(name, "ko", target_world_id=name, remapped=False) == []
    assert demos.translations(name, "ja", target_world_id=name, remapped=False) == []


def test_entries_keep_their_ids_in_the_demos_own_world(folder) -> None:
    demos = folder(_full())
    name = PACKAGED["world"]["id"]
    entries = demos.translations(name, "ko", target_world_id=name, remapped=False)
    texts = demos.texts(name, target_world_id=name, remapped=False)
    assert {e.key for e in entries} == set(texts) and len(entries) == len(_texts())


def test_entries_move_with_a_remapped_world(folder) -> None:  # BR-V3-18·19·20
    data = _full()
    data["entries"].append(
        {"kind": "region", "id": "region-nowhere", "field": "name", "source": "x", "text": "y"}
    )
    demos = folder(data)
    name = PACKAGED["world"]["id"]
    entries = demos.translations(name, "ko", target_world_id="w2", remapped=True)
    texts = demos.texts(name, target_world_id="w2", remapped=True)
    keys = {e.key for e in entries}
    assert keys - set(texts) == {
        ("region", "region-nowhere", "name")
    }  # outside the file: kept as is
    assert set(texts) <= keys
    world = [e for e in entries if e.kind == "world"]
    assert world and {e.id for e in world} == {"w2"}  # the world entry is the target id
    region = PACKAGED["regions"][0]["id"]
    assert ("region", remapped_id("w2", region), "name") in keys


# --- the packaged Korean version (Step 6, BR-V3-07, Q1=A) ------------------------------ #
FORBIDDEN_KO = (
    "메이플",
    "빅토리아",
    "헤네시스",
    "엘리니아",
    "페리온",
    "커닝",
    "리스 항구",
    "슬리피우드",
    "노틸러스",
    "검은 마법사",
)
SENTENCE_FIELDS = {
    ("world", "description"),
    ("region", "description"),
    ("npc", "description"),
    ("event_seed", "description"),
    ("knowledge", "statement"),
}


def _packaged_entries():
    demos = DemoWorlds()
    name = demos.list()[0].name
    assert "ko" in demos.translation_langs(name)
    return demos, name, demos.translations(name, "ko", target_world_id=name, remapped=False)


def test_the_packaged_demo_is_fully_translated_with_no_problem() -> None:
    demos, name, entries = _packaged_entries()
    assert demos.problems == []  # the CI check (check_packaged) is clean
    assert {e.key for e in entries} == set(demos.texts(name, target_world_id=name, remapped=False))
    assert demos.card(name, "ko") is not None


def test_the_packaged_korean_follows_the_style() -> None:
    _demos, _name, entries = _packaged_entries()
    for e in entries:
        where = f"{e.kind} {e.id}.{e.field}"
        assert not any(w in e.text for w in FORBIDDEN_KO), where  # BR-U8-10 in Korean too
        if (e.kind, e.field) in SENTENCE_FIELDS:
            assert e.text.endswith("다."), where  # story register (V2 Q2=A)
        else:
            assert not e.text.endswith("."), where  # names, roles, titles: value names
        if e.field == "name":
            assert not any("a" <= c.lower() <= "z" for c in e.text), where  # transliterated
