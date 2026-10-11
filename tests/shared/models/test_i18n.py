"""Translation entries and files (V3, FD domain-entities § 2, BR-V3-01·04·05, TP-V3-1·2)."""

from __future__ import annotations

import hashlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from locus.localization import source_hash as localization_source_hash
from locus.shared.models import (
    TRANSLATABLE_FIELDS,
    TranslationEntry,
    TranslationFile,
    source_hash,
)

# text that is not blank: Hangul, emoji, accents and inner spaces mixed in
_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=40
).filter(lambda t: t.strip())


@st.composite
def _entries(draw) -> TranslationEntry:
    kind = draw(st.sampled_from(sorted(TRANSLATABLE_FIELDS)))
    return TranslationEntry(
        kind=kind,
        id=draw(st.text(min_size=1, max_size=12).filter(lambda t: t.strip())),
        field=draw(st.sampled_from(TRANSLATABLE_FIELDS[kind])),
        source=draw(_text),
        text=draw(_text),
    )


_files = st.builds(
    TranslationFile,
    lang=st.sampled_from(["ko", "ja", "de"]),
    world_id=st.text(min_size=1, max_size=12),
    entries=st.lists(_entries(), max_size=8),
)


@given(_files)
def test_a_translation_file_round_trips(file: TranslationFile) -> None:  # TP-V3-1, PBT-02
    data = file.to_json()
    assert TranslationFile.parse(data) == file
    assert TranslationFile.parse(data).to_json() == data


@pytest.mark.parametrize(
    ("data", "why"),
    [
        ([], "JSON object"),
        ({"format": "other", "version": 1, "lang": "ko", "world_id": "w"}, "not a translation"),
        ({"format": "locus.translations", "version": 2, "lang": "ko", "world_id": "w"}, "version"),
        ({"format": "locus.translations", "version": 1, "lang": "kor", "world_id": "w"}, "lang"),
    ],
)
def test_a_file_of_another_shape_is_refused(data: object, why: str) -> None:
    with pytest.raises(ValueError, match=why):
        TranslationFile.parse(data)


def test_an_entry_names_a_field_of_its_kind_and_carries_text() -> None:
    TranslationEntry(kind="npc", id="npc-brisa", field="role", source="archer", text="궁수")
    with pytest.raises(ValueError, match="no translatable field"):
        TranslationEntry(kind="region", id="r", field="role", source="x", text="y")
    with pytest.raises(ValueError, match="empty translation"):
        TranslationEntry(kind="region", id="r", field="name", source="x", text="  ")
    with pytest.raises(ValueError, match="empty source"):
        TranslationEntry(kind="region", id="r", field="name", source=" ", text="y")


def test_the_hash_ignores_the_ends_and_did_not_change_when_it_moved() -> None:  # TP-V3-2
    assert source_hash("Saltwake Harbor") == source_hash("  Saltwake Harbor\n")
    assert source_hash("Saltwake Harbor") != source_hash("Saltwake Harbour")
    # the value the cache already holds rows under (sha256 of the stripped text)
    assert source_hash(" Ironcrag ") == hashlib.sha256(b"Ironcrag").hexdigest()
    assert localization_source_hash is source_hash  # re-exported, one function


def test_an_entry_hashes_its_source() -> None:
    e = TranslationEntry(
        kind="world", id="emberleaf", field="name", source="Emberleaf Isle", text="엠버리프 섬"
    )
    assert e.key == ("world", "emberleaf", "name")
    assert e.source_hash == source_hash("Emberleaf Isle")
