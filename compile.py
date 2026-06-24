"""
compile.py — CLI for the Object-Oriented Prompt Composition System
"""
import argparse
import json
import sys
import os
from compiler import PromptCompiler, SceneObject

def main():
    parser = argparse.ArgumentParser(description="Compile structured scene facts into natural language prompts.")
    parser.add_argument("scene_file", help="Path to the scene JSON file")
    parser.add_argument("--profile", help="Override the render profile (e.g. portrait, fashion, cinematic, character_sheet)")
    parser.add_argument("--mode", choices=["fact_chain", "scene_description"], help="Override the narrative mode")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation and exit")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode to fail compilation on hard errors")
    parser.add_argument("--data-dir", default="data", help="Directory containing configuration JSON files")

    args = parser.parse_args()

    if not os.path.exists(args.scene_file):
        print(f"Error: Scene file '{args.scene_file}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.scene_file, "r", encoding="utf-8") as f:
            scene = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{args.scene_file}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        compiler = PromptCompiler(data_dir=args.data_dir)
    except Exception as e:
        print(f"Error initializing compiler: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve scene objects for validation
    scene_objects = {
        obj_id: SceneObject(obj_id, obj_data.get("type"), obj_data)
        for obj_id, obj_data in scene.get("objects", {}).items()
    }

    errors = compiler.validation_system.validate(scene, scene_objects)
    
    if errors:
        print("Validation report:")
        has_error = False
        for err in errors:
            print(f"  [{err.severity.upper()}] {err.message}")
            if err.severity == "error":
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
        prompt = compiler.compile_scene(scene, strict=args.strict)
        print(prompt)
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
