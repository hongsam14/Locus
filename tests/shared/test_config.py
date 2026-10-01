"""U5 settings — dialogue knobs, display languages, and the provider retry pin (Step 2.4)."""

from __future__ import annotations

import sys
import types

import pytest
from pydantic import ValidationError

from locus.shared.config import Settings

_KEYS = (
    "NPC_MAX_FACTS",
    "NPC_MAX_RUMORS",
    "NPC_MAX_RECENT_MESSAGES",
    "NPC_MAX_MESSAGE_CHARS",
    "SUPPORTED_LANGS",
    "TRANSLATION_TARGET_LANG",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_dialogue_knobs_default_and_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    t = _settings().play_tuning()
    assert (t.npc_max_facts, t.npc_max_rumors, t.npc_max_recent_messages) == (12, 8, 10)
    assert t.npc_max_message_chars == 500
    monkeypatch.setenv("NPC_MAX_FACTS", "3")
    monkeypatch.setenv("NPC_MAX_RUMORS", "0")
    monkeypatch.setenv("NPC_MAX_RECENT_MESSAGES", "4")
    monkeypatch.setenv("NPC_MAX_MESSAGE_CHARS", "80")
    t = _settings().play_tuning()
    assert (t.npc_max_facts, t.npc_max_rumors, t.npc_max_recent_messages) == (3, 0, 4)
    assert t.npc_max_message_chars == 80
    monkeypatch.setenv("NPC_MAX_MESSAGE_CHARS", "0")
    with pytest.raises(ValidationError):
        _settings()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ko,en", ("ko", "en")),  # the comma form that a tuple field would fail to decode
        (" KO , en ,", ("ko", "en")),
        ("", ("ko", "en")),  # empty falls back to the defaults
        ("ko", ("ko",)),
    ],
)
def test_supported_langs_parse_the_comma_form(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: tuple[str, ...]
) -> None:
    monkeypatch.setenv("SUPPORTED_LANGS", raw)
    assert _settings().supported_langs == expected


def test_the_default_display_language_must_be_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    """FD review R-04: a default outside the set would 400 every request without ?lang=."""
    monkeypatch.setenv("SUPPORTED_LANGS", "ko,en")
    monkeypatch.setenv("TRANSLATION_TARGET_LANG", "fr")
    with pytest.raises(ValidationError, match="not in SUPPORTED_LANGS"):
        _settings()
    monkeypatch.setenv("TRANSLATION_TARGET_LANG", "EN")  # case-insensitive
    assert _settings().translation_target_lang == "EN"


def test_both_providers_pin_sdk_retries_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR review R-01: retries live only in `with_retry` (bounded; see retry.py)."""
    seen: list[dict] = []

    class RecordingChatOpenAI:
        def __init__(self, **kwargs) -> None:
            seen.append(kwargs)

    fake = types.ModuleType("langchain_openai")
    fake.ChatOpenAI = RecordingChatOpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_openai", fake)

    from locus.shared.llm.openai_provider import OpenAILLMProvider, OpenAIVLMProvider

    OpenAILLMProvider(api_key="k", model="m")
    OpenAIVLMProvider(api_key="k", model="m")
    assert [kw["max_retries"] for kw in seen] == [0, 0]
    assert all(kw["timeout"] == 30.0 for kw in seen)


def test_review_10_the_embedding_client_is_bounded_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review U5 #10: the SDK default (2 retries, no timeout) stacked under with_retry."""
    seen: list[dict] = []

    class RecordingEmbeddings:
        def __init__(self, **kwargs) -> None:
            seen.append(kwargs)

    fake = types.ModuleType("langchain_openai")
    fake.OpenAIEmbeddings = RecordingEmbeddings  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_openai", fake)

    from locus.shared.llm.openai_provider import OpenAIEmbeddingProvider

    OpenAIEmbeddingProvider(api_key="k", model="m", dimension=8)
    assert seen[0]["max_retries"] == 0 and seen[0]["timeout"] == 30.0


def test_u6_deed_knobs_default_and_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """U6 domain-entities §5: six knobs, env-overridable."""
    t = _settings().play_tuning()
    assert (t.spread_min_weight, t.deed_seed_min_salience) == (0.15, 0.5)
    assert (t.max_spread_per_region_turn, t.declare_max_chars) == (1, 300)
    assert (t.npc_max_deeds, t.appraisal_max_deeds) == (5, 8)
    for name, value in (
        ("SPREAD_MIN_WEIGHT", "0.3"),
        ("DEED_SEED_MIN_SALIENCE", "0.7"),
        ("MAX_SPREAD_PER_REGION_TURN", "2"),
        ("DECLARE_MAX_CHARS", "120"),
        ("NPC_MAX_DEEDS", "0"),
        ("APPRAISAL_MAX_DEEDS", "3"),
    ):
        monkeypatch.setenv(name, value)
    t = _settings().play_tuning()
    assert (t.spread_min_weight, t.deed_seed_min_salience) == (0.3, 0.7)
    assert (t.max_spread_per_region_turn, t.declare_max_chars) == (2, 120)
    assert (t.npc_max_deeds, t.appraisal_max_deeds) == (0, 3)
    monkeypatch.setenv("DECLARE_MAX_CHARS", "0")
    with pytest.raises(ValidationError):
        _settings()


# --- U7 tuning in one place (FR-A7 / US-8.5, TP-U7-8, BR-U7-19/20) --------------------- #
def test_tp_u7_8_default_settings_build_the_dataclass_defaults() -> None:
    from locus.shared.config.tuning import KnowledgeTuning, PlayTuning, WorldTuning

    s = _settings()
    assert s.knowledge_tuning() == KnowledgeTuning()
    assert s.play_tuning() == PlayTuning()
    world = s.world_tuning()
    default = WorldTuning()
    assert dict(world.base_weights) == dict(default.base_weights)
    assert dict(world.terrain_modifiers) == dict(default.terrain_modifiers)
    assert (world.default_base, world.dedup_threshold) == (0.5, 0.86)


@pytest.mark.parametrize(
    ("env", "value", "read"),
    [
        ("CONSENSUS_PROPAGATE_MIN", "0.6", lambda s: s.knowledge_tuning().propagate_min),
        ("CONSENSUS_HEARSAY_MIN", "0.1", lambda s: s.knowledge_tuning().hearsay_min),
        ("ONTOLOGY_DEDUP_THRESHOLD", "0.9", lambda s: s.world_tuning().dedup_threshold),
        ("TOPOLOGY_DEFAULT_BASE", "0.4", lambda s: s.world_tuning().default_base),
        ("RUMOR_HIGH_SUPPORT_THRESHOLD", "0.5", lambda s: s.play_tuning().high_support_threshold),
        ("RUMOR_FEEDBACK_CAP", "0.2", lambda s: s.play_tuning().feedback_cap),
        ("RUMOR_FEEDBACK_RESTORE", "0.1", lambda s: s.play_tuning().feedback_restore),
        ("RUMOR_PROMOTION_THRESHOLD", "0.7", lambda s: s.play_tuning().promotion_threshold),
        ("EVENT_MAX_DELTA", "0.1", lambda s: s.play_tuning().event_max_delta),
        ("EVENT_PROPAGATE_MIN", "0.2", lambda s: s.play_tuning().event_propagate_min),
        ("EVENT_SUPPORT_REINFORCE", "0.05", lambda s: s.play_tuning().event_support_reinforce),
        ("EVENT_SUGGEST_MAX", "3", lambda s: s.play_tuning().max_event_suggestions),
        ("EVENT_SUGGEST_MAX_REGIONS", "12", lambda s: s.play_tuning().suggest_max_regions),
    ],
)
def test_tp_u7_8_each_knob_reaches_its_tuning(
    monkeypatch: pytest.MonkeyPatch, env: str, value: str, read
) -> None:
    monkeypatch.setenv(env, value)
    assert read(_settings()) == type(read(_settings()))(value)


def test_tp_u7_8_table_env_overrides_only_the_named_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOPOLOGY_BASE_WEIGHTS", '{"route": 0.7}')
    monkeypatch.setenv("TOPOLOGY_TERRAIN_MODIFIERS", '{" Swamp ": 0.6}')
    w = _settings().world_tuning()
    assert (w.base_weights["route"], w.base_weights["adjacent"]) == (0.7, 0.8)
    assert (w.terrain_modifiers["swamp"], w.terrain_modifiers["road"]) == (0.6, 1.2)


@pytest.mark.parametrize(
    ("env", "value"),
    [
        ("TOPOLOGY_BASE_WEIGHTS", "{broken"),  # not JSON
        ("TOPOLOGY_BASE_WEIGHTS", '{"route": 1.2}'),  # out of range
        ("TOPOLOGY_BASE_WEIGHTS", '{"teleport": 0.5}'),  # unknown connection kind
        ("TOPOLOGY_TERRAIN_MODIFIERS", '{"road": -1}'),
        ("CONSENSUS_HEARSAY_MIN", "0.6"),  # above propagate_min 0.5
        ("EVENT_MAX_DELTA", "1.5"),
        ("EVENT_SUGGEST_MAX", "0"),
    ],
)
def test_br_u7_20_a_bad_knob_fails_startup(
    monkeypatch: pytest.MonkeyPatch, env: str, value: str
) -> None:
    monkeypatch.setenv(env, value)
    with pytest.raises(ValueError):  # ValidationError and SettingsError are ValueErrors
        _settings()
