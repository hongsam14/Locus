"""V3: the translatable texts of a World File, and ids that move with a remap
(FD BLM § 5, BR-V3-04·18·20, TP-V3-3)."""

from __future__ import annotations

from hypothesis import given, settings

from locus.world.demo import DemoWorlds
from locus.world.worldfile import file_ids, remap_ids, remapped_id, translatable_texts
from locus.world.worldfile.schema import WorldFile
from tests.world.strategies import world_files


@settings(max_examples=60, deadline=None)
@given(world_files())
def test_remap_ids_moves_every_file_id_by_remapped_id(file: WorldFile) -> None:
    moved = remap_ids(file, "dst")
    assert file_ids(moved) == {remapped_id("dst", i) for i in file_ids(file)}


@settings(max_examples=60, deadline=None)
@given(world_files())
def test_the_texts_of_a_remapped_file_are_the_same_texts_under_moved_keys(file: WorldFile) -> None:
    before = translatable_texts(file)
    after = translatable_texts(remap_ids(file, "dst"))

    def move(key: tuple[str, str, str]) -> tuple[str, str, str]:
        kind, id_, field = key
        return (kind, "dst" if kind == "world" else remapped_id("dst", id_), field)

    assert after == {move(k): v for k, v in before.items()}


def test_blank_texts_are_not_targets() -> None:
    file = WorldFile.model_validate(
        {"format_version": 1, "world": {"id": "w", "name": "Isle", "description": "  "}}
    )
    assert translatable_texts(file) == {("world", "w", "name"): "Isle"}


def test_the_packaged_demo_has_123_texts() -> None:
    demos = DemoWorlds()
    file = demos.load_file(demos.list()[0].name)
    texts = translatable_texts(file)
    kinds = [k for k, _i, _f in texts]
    assert len(texts) == 123
    assert {k: kinds.count(k) for k in set(kinds)} == {
        "world": 2,
        "region": 24,
        "npc": 45,
        "event_seed": 6,
        "knowledge": 46,
    }
