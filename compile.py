"""
compile.py — CLI for the Object-Oriented Prompt Composition System
"""
import argparse
import json
import sys
import os
from compiler import PromptCompiler, validate


_SUBJECT_KEYWORDS = {
    "man": {"gender": "man", "subject": "professional_man"},
    "woman": {"gender": "woman", "subject": "urban_influencer"},
    "person": {"gender": "person"},
    "orc": {"gender": "orc", "subject": "orc_warrior", "type": "creature"},
    "elf": {"gender": "elf", "subject": "elf_archer", "type": "creature"},
}

_ENVIRONMENT_KEYWORDS = {
    "cafe", "alley", "beach", "forest", "office", "bedroom",
    "bathroom", "rooftop", "poolside", "balcony", "car_interior", "server_room",
}

_ACTION_KEYWORDS = {
    "holding": "holding",
    "holds": "holding",
    "sitting": "sitting",
    "sits": "sitting",
    "leaning": "leaning_on",
    "leans": "leaning_on",
    "standing": "standing_next_to",
    "stands": "standing_next_to",
    "looking": "looking_at",
    "looks": "looking_at",
    "hugging": "hugging",
    "hugs": "hugging",
    "inside": "inside",
}

_EXPRESSION_KEYWORDS = {
    "smiling": "smiling",
    "smile": "smiling",
    "serious": "serious",
    "happy": "smiling",
    "sad": "sad",
    "angry": "angry",
    "confident": "confident",
    "thoughtful": "thoughtful",
    "focused": "focused",
    "shocked": "shocked",
    "determined": "determined",
    "relaxed": "relaxed",
}


def _parse_simple(text: str) -> dict:
    """Parse a simple comma-separated description into a scene JSON.

    Format: "<subject>, <expression>, <action> <object>, in <environment>"
    Example: "woman, smiling, holding coffee, in cafe"
    """
    parts = [p.strip() for p in text.split(",")]

    scene = {
        "camera": {"framing": "full_body"},
        "render_profile": "cinematic",
        "objects": {},
        "relationships": [],
    }

    expression = ""
    action_type = None
    action_target = None  # object or dot-notation anchor
    env_type = None

    for part in parts:
        part_lower = part.lower()

        # Check for "in <environment>"
        if part_lower.startswith("in "):
            env_candidate = part[3:].strip().lower().replace(" ", "_")
            if env_candidate in _ENVIRONMENT_KEYWORDS:
                env_type = env_candidate
            else:
                env_type = env_candidate
            continue

        # Check if this is a subject keyword
        if part_lower in _SUBJECT_KEYWORDS:
            info = _SUBJECT_KEYWORDS[part_lower]
            scene["objects"]["h1"] = {
                "type": info.get("type", "human"),
                "gender": info["gender"],
            }
            if "subject" in info:
                scene["objects"]["h1"]["subject"] = info["subject"]
            continue

        # Check for expression
        if part_lower in _EXPRESSION_KEYWORDS:
            expression = _EXPRESSION_KEYWORDS[part_lower]
            continue

        # Check for action phrase: "holding coffee", "sitting", etc.
        for keyword, action_id in sorted(_ACTION_KEYWORDS.items(), key=lambda x: -len(x[0])):
            if part_lower.startswith(keyword + " ") or part_lower == keyword:
                action_type = action_id
                rest = part[len(keyword):].strip()
                if rest:
                    action_target = rest
                break

    # Set expression
    if expression and "h1" in scene["objects"]:
        scene["objects"]["h1"]["Face"] = {"expression": expression}

    # Set environment
    if env_type:
        scene["environment"] = {"type": env_type}

    # Set relationship
    if action_type:
        rel = {"type": action_type, "actor": "h1"}
        if action_target and "." in action_target:
            rel["target"] = action_target
        elif action_target:
            # Create an object for the target
            obj_id = "obj_1"
            template_key = "".join(w.capitalize() for w in action_target.split("_"))
            scene["objects"][obj_id] = {
                "type": "item",
                "template_key": template_key,
            }
            rel["object"] = obj_id
        scene["relationships"] = [rel]

    return scene


def main():
    parser = argparse.ArgumentParser(description="Compile structured scene facts into natural language prompts.")
    parser.add_argument("scene_file", nargs="?", default=None, help="Path to the scene JSON file (optional when using --simple)")
    parser.add_argument("--profile", help="Override the render profile (e.g. portrait, fashion, cinematic, character_sheet)")
    parser.add_argument("--mode", choices=["fact_chain", "scene_description"], help="Override the narrative mode")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation and exit")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode to fail compilation on hard errors")
    parser.add_argument("--no-camera-text", action="store_true", help="Disable automatic injection of camera framing descriptor")
    parser.add_argument("--data-dir", default="data", help="Directory containing configuration JSON files")
    parser.add_argument("--simple", type=str, help="Quick shorthand: 'woman, smiling, holding coffee, in cafe'")

    args = parser.parse_args()

    if args.simple:
        scene = _parse_simple(args.simple)
    elif args.scene_file:
        if not os.path.exists(args.scene_file):
            print(f"Error: Scene file '{args.scene_file}' not found.", file=sys.stderr)
            sys.exit(1)
        try:
            with open(args.scene_file, "r", encoding="utf-8") as f:
                scene = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from '{args.scene_file}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Provide either a scene file or --simple.", file=sys.stderr)
        sys.exit(1)

    try:
        compiler = PromptCompiler(data_dir=args.data_dir)
    except Exception as e:
        print(f"Error initializing compiler: {e}", file=sys.stderr)
        sys.exit(1)

    # Pre-flight validation
    errors = validate(scene, compiler.actions_db,
                      compiler.spatial_db, compiler.subjects_db)
    if errors:
        print("Validation report:")
        has_error = False
        for err in errors:
            print(f"  [{err['severity'].upper()}] {err['message']}")
            if err['severity'] == "error":
                has_error = True
        if args.validate_only:
            sys.exit(1 if has_error else 0)
    elif args.validate_only:
        print("Validation passed with 0 errors/warnings.")
        sys.exit(0)

    # Apply overrides
    if args.profile:
        scene["render_profile"] = args.profile

    profile_name = scene.get("render_profile", "character_sheet")
    
    # Overriding narrative_mode in render profile if --mode is provided
    if args.mode:
        if profile_name in compiler.render_system.profiles:
            profile_override = dict(compiler.render_system.profiles[profile_name])
            profile_override["narrative_mode"] = args.mode
            compiler.render_system.profiles[profile_name] = profile_override
        else:
            compiler.render_system.profiles[profile_name] = {
                "include_tags": ["identity", "emotion", "clothing", "accessory", "action", "interaction", "style", "spatial", "environment", "lighting", "weather", "composition"],
                "max_fragments": 99,
                "narrative_mode": args.mode
            }

    try:
        prompt = compiler.compile_scene(scene, strict=args.strict, inject_camera_descriptor=not args.no_camera_text)
        print(prompt)
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
