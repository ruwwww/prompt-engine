import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from compiler import PromptCompiler

compiler = PromptCompiler()
pytestmark = pytest.mark.stress

SCENARIO_PROFESSIONAL = {
    "output_format": "labeled",
    "camera": {"framing": "low_angle", "shot_type": "medium"},
    "environment": "modern_office",
    "objects": {
        "woman_1": {"type": "human", "subject": "professional_woman", "gender": "woman"},
        "laptop_1": {"type": "object", "label": "silver laptop", "details": "with a glowing Apple logo"},
        "glass_1": {"type": "object", "label": "glass of water", "details": "with a slice of lemon"},
        "desk_1": {"type": "fixture", "fixture_name": "desk", "label": "transparent glass desk", "details": "with sleek metal legs"}
    },
    "relationships": [
        {"type": "sitting_at", "actor": "woman_1", "target": "desk_1"}
    ]
}

SCENARIO_PROPOSAL = {
    "output_format": "labeled",
    "environment": "romantic_beach",
    "objects": {
        "man_1": {"type": "human", "subject": "man", "gender": "man"},
        "woman_1": {"type": "human", "subject": "woman", "gender": "woman"},
        "rose_arch_1": {
            "type": "fixture",
            "label": "massive heart-shaped arch",
            "details": "made entirely of red roses with glowing 'Happy Valentine Day' text"
        },
        "ring_box_1": {"type": "object", "label": "small velvet ring box"}
    },
    "relationships": [
        {"type": "kneeling_before", "actor": "man_1", "target": "woman_1"},
        {"type": "holding", "actor": "man_1", "object": "ring_box_1"},
        {"type": "framing", "object": "rose_arch_1", "subjects": ["man_1", "woman_1"]}
    ]
}

SCENARIO_ORC = {
    "output_format": "labeled",
    "environment": "rainy_alley",
    "camera": {"framing": "full_body"},
    "objects": {
        "orc_1": {
            "type": "human", "subject": "orc_warrior",
            "Face": {"expression": "snarling"},
            "Tusks": {"size": "large", "material": "ivory"},
            "UpperBody": {"owned_item_id": "chainmail_1"},
            "LowerBody": {"owned_item_id": "leather_pants_1"},
            "Feet": {"owned_item_id": "iron_boots_1"},
            "body_config": {
                "arms": {"left": "at_side", "right": "raised"},
                "gaze": {"direction": "toward_camera"}
            }
        },
        "axe_1": {"type": "object", "label": "massive battle-axe"},
        "wall_1": {"type": "fixture", "label": "graffiti-covered brick wall"}
    },
    "relationships": [
        {"type": "holding", "actor": "orc_1", "object": "axe_1"},
        {"type": "standing_next_to", "actor": "orc_1", "target": "wall_1"}
    ]
}

SCENARIO_MINIMAL = {
    "output_format": "labeled",
    "camera": {"framing": "medium"},
    "objects": {
        "h1": {"type": "human", "subject": "urban_influencer"}
    }
}

SCENARIO_MAXIMAL = {
    "output_format": "labeled",
    "environment": "busy_street",
    "objects": {
        "actor_1": {"type": "human", "subject": "man", "gender": "man"},
        "actor_2": {"type": "human", "subject": "woman", "gender": "woman"},
        "actor_3": {"type": "human", "subject": "child"},
        "car_1": {"type": "object", "label": "red sports car"},
        "balloon_1": {"type": "object", "label": "red balloon"},
        "bench_1": {"type": "fixture", "label": "wooden park bench"}
    },
    "relationships": [
        {"type": "standing_next_to", "actor": "actor_1", "target": "actor_2"},
        {"type": "sitting_on", "actor": "actor_3", "target": "bench_1"},
        {"type": "holding", "actor": "actor_3", "object": "balloon_1"}
    ]
}

SCENARIO_CONFLICT = {
    "objects": {
        "h1": {"type": "human"},
        "desk_1": {"type": "fixture", "label": "wooden desk"},
        "laptop_1": {"type": "object", "label": "laptop"}
    },
    "relationships": [
        {"type": "sitting_at", "actor": "h1", "target": "desk_1"},
        {"type": "holding", "actor": "h1", "object": "laptop_1"}
    ]
}


def assert_prompt_contains(output, *expected_phrases):
    """Helper to ensure the final prompt contains critical strings."""
    for phrase in expected_phrases:
        assert phrase in output, f"Expected '{phrase}' in output, but got:\n{output}"


def test_stress_professional():
    try:
        output = compiler.compile_scene(SCENARIO_PROFESSIONAL)
        assert_prompt_contains(
            output,
            "transparent glass desk",
            "silver laptop",
            "glass of water",
            "modern office"
        )
    except Exception as e:
        print(f"\n--- FAILURE: Scenario A (Professional) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise


def test_stress_proposal():
    try:
        output = compiler.compile_scene(SCENARIO_PROPOSAL)
        assert_prompt_contains(
            output,
            "kneeling before a woman",
            "heart-shaped arch",
            "framing a man and a woman",
            "soft sandy shore"
        )
    except Exception as e:
        print(f"\n--- FAILURE: Scenario B (Proposal) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise


def test_stress_orc():
    try:
        output = compiler.compile_scene(SCENARIO_ORC)
        assert_prompt_contains(
            output,
            "snarling orc",
            "massive battle-axe",
            "narrow alley",
            "graffiti-covered"
        )
    except Exception as e:
        print(f"\n--- FAILURE: Scenario C (Orc) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise


def test_stress_minimalist():
    try:
        output = compiler.compile_scene(SCENARIO_MINIMAL)
        assert output  # Ensure it's not empty
        assert "Subject:" in output  # Ensure it generates the labeled format
        assert not output.startswith("Error:")  # Ensure no raw crash messages
    except Exception as e:
        print(f"\n--- FAILURE: Scenario D (Minimalist) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise


def test_stress_maximal():
    try:
        # This is less about specific phrases and more about ensuring it doesn't crash/truncate
        output = compiler.compile_scene(SCENARIO_MAXIMAL)
        assert len(output) > 200  # Ensure it generates a long prompt
        assert "Subject:" in output  # Ensure labeled format persists
    except Exception as e:
        print(f"\n--- FAILURE: Scenario E (Maximal) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise


def test_stress_conflict():
    try:
        output = compiler.compile_scene(SCENARIO_CONFLICT)
        # It should render both actions gracefully
        assert "sitting at" in output or "sits at" in output or "seated comfortably at" in output
        assert "holding" in output
    except Exception as e:
        print(f"\n--- FAILURE: Scenario F (Conflict) ---")
        print(f"Exception: {e}")
        print(f"Output snippet: {output[:500] if 'output' in locals() else 'No output generated'}")
        raise
