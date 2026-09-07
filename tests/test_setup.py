from pathlib import Path

from agent_hub.setup import INSTRUCTIONS, merge_managed_block


def test_managed_instruction_block_is_idempotent_and_preserves_existing(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# Existing\n\nKeep me.\n", encoding="utf-8")
    merge_managed_block(path)
    first = path.read_text(encoding="utf-8")
    merge_managed_block(path)
    assert path.read_text(encoding="utf-8") == first
    assert "Keep me." in first
    assert INSTRUCTIONS.strip() in first


def test_managed_instructions_require_a_stable_cli_session() -> None:
    assert "stable session ID" in INSTRUCTIONS


def test_managed_instructions_require_a_model_declaration() -> None:
    assert "model id" in INSTRUCTIONS
    assert "hub_get_brief" in INSTRUCTIONS
    assert "matching your tier" in INSTRUCTIONS
