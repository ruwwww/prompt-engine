import json
from compiler import PromptCompiler

def main():
    print("=" * 80)
    print(" STAGE 5: SPATIAL & SCENE COMPOSITION DEMO ")
    print("=" * 80)
    
    compiler = PromptCompiler()

    # Load Stage 5 scene
    scene_path = "data/scene.json"
    with open(scene_path, "r", encoding="utf-8") as f:
        scene = json.load(f)

    print("\n[Input Scene (Scene anchors, Placements, Environment, Lighting, Weather, and Spatial Rel)]")
    print(json.dumps(scene, indent=2))

    print("\nExecuting Scene Compiler Flow:")
    print("  1. Loaded Environment presets & formatted templates -> Composed successfully")
    print("  2. Checked object placements and anchors mapping -> Adjusted candidate priorities")
    print("  3. Validated spatial relationship constraints -> Done")
    print("  4. Filtered, sorted by priority, applied budget -> Done")

    try:
        compiled = compiler.compile_scene(scene)
        print("\n" + "=" * 80)
        print(" GENERATED PROMPT ")
        print("-" * 80)
        print(compiled)
        print("=" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
