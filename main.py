"""
main.py — Prompt Engine demo: all stages + architecture polish
"""
import json
from compiler import PromptCompiler

DIVIDER = "=" * 80

def section(title):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)

def show(label, prompt):
    print(f"\n  [{label}]")
    print(f"  {prompt}")

def main():
    c = PromptCompiler()

    # ------------------------------------------------------------------ #
    # Demo 1: fact_chain mode (current default)
    # ------------------------------------------------------------------ #
    section("DEMO 1 — Fact-chain mode  (default)")

    scene_base = {
        "camera": {"framing": "full_body"},
        "pose": "standing",
        "render_profile": "cinematic",
        "environment": {"type": "alley", "lighting": "neon", "weather": "rainy"},
        "composition": {"type": "cinematic"},
        "anchors": {"primary": "h1"},
        "placements": {"car_1": "background"},
        "objects": {
            "h1": {"type": "human", "persona": "urban_influencer"},
            "car_1": {"type": "vehicle", "template_key": "Car", "color": "red"},
        },
        "relationships": [{"type": "standing_next_to", "subject": "h1", "target": "car_1"}],
    }

    show("cinematic profile", c.compile_scene(scene_base))

    # ------------------------------------------------------------------ #
    # Demo 2: scene_description mode (Phase 5)
    # ------------------------------------------------------------------ #
    section("DEMO 2 — Scene-description mode  (narrative sentence)")

    c.render_system.profiles["cinematic"]["narrative_mode"] = "scene_description"
    show("cinematic profile", c.compile_scene(scene_base))
    del c.render_system.profiles["cinematic"]["narrative_mode"]  # restore default

    # ------------------------------------------------------------------ #
    # Demo 3: Render profile comparison
    # ------------------------------------------------------------------ #
    section("DEMO 3 — Render profile comparison (same scene, different focus)")

    scene_rich = {
        "camera": {"framing": "full_body"},
        "pose": "standing",
        "objects": {
            "h1": {"type": "human", "persona": "urban_influencer"},
            "hoodie_1": {"type": "clothing", "template_key": "Hoodie",
                          "fit": "oversized", "color": "black", "material": "cotton"},
            "pants_1": {"type": "clothing", "template_key": "CargoPants",
                         "fit": "baggy", "color": "olive"},
            "c1": {"type": "drink", "template_key": "CoffeeCup",
                    "material": "ceramic", "color": "white"},
        },
        "relationships": [{"type": "holding", "actor": "h1", "object": "c1"}],
    }

    for profile in ("portrait", "fashion", "character_sheet"):
        scene_rich["render_profile"] = profile
        show(profile, c.compile_scene(scene_rich))

    # ------------------------------------------------------------------ #
    # Demo 4: Pose occlusion
    # ------------------------------------------------------------------ #
    section("DEMO 4 — Pose occlusion  (holding coffee disappears when hands hidden)")

    scene_hold = {
        "camera": {"framing": "medium"},
        "render_profile": "character_sheet",
        "objects": {
            "h1": {"type": "human", "persona": "urban_influencer"},
            "c1": {"type": "drink", "template_key": "CoffeeCup",
                    "material": "ceramic", "color": "white"},
        },
        "relationships": [{"type": "holding", "actor": "h1", "object": "c1"}],
    }
    scene_hold["pose"] = "standing"
    show("standing pose", c.compile_scene(scene_hold))
    scene_hold["pose"] = "hands_behind_back"
    show("hands_behind_back pose", c.compile_scene(scene_hold))

    # ------------------------------------------------------------------ #
    # Demo 5: Multi-character
    # ------------------------------------------------------------------ #
    section("DEMO 5 — Multi-character scene")

    scene_multi = {
        "camera": {"framing": "full_body"},
        "render_profile": "character_sheet",
        "objects": {
            "h1": {"type": "human", "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "Hair": {"color": "brown", "length": "long", "style": "wavy"}},
            "h2": {"type": "human", "gender": "man",
                    "Face": {"expression": "serious"},
                    "Hair": {"color": "black", "length": "short", "style": "straight"}},
        },
    }
    show("two humans", c.compile_scene(scene_multi))

    # ------------------------------------------------------------------ #
    # Demo 6: Validation system
    # ------------------------------------------------------------------ #
    section("DEMO 6 — Validation system")

    scene_bad = {
        "camera": {"framing": "full_body"},
        "objects": {"h1": {"type": "human", "gender": "woman"}},
        "anchors": {"primary": "ghost_object"},
        "relationships": [{"type": "teleporting", "actor": "h1"}],
    }
    errors = c.validation_system.validate(
        scene_bad,
        {oid: __import__("compiler").SceneObject(oid, od.get("type"), od)
         for oid, od in scene_bad["objects"].items()}
    )
    print()
    for e in errors:
        print(f"  [{e.severity.upper()}] {e.message}")

    print(f"\n{DIVIDER}\n")


if __name__ == "__main__":
    main()
