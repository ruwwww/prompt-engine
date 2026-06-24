import json
from compiler import PromptCompiler

def main():
    print("=" * 80)
    print(" STAGE 6: NARRATIVE COMPOSITION ENGINE DEMO ")
    print("=" * 80)
    
    compiler = PromptCompiler()

    # Load Stage 6 scene
    scene_path = "data/scene.json"
    with open(scene_path, "r", encoding="utf-8") as f:
        scene = json.load(f)

    print("\n[Input Scene Facts]")
    print("- Human (Woman, smiling, long wavy brown hair) wearing black cotton hoodie.")
    print("- Location: alley (neon lighting, rainy weather).")
    print("- Actions: Standing next to a red car in background.")

    print("\nExecuting Narrative Graph Compilation Flow:")
    print("  1. Resolved Subject Description Attachment (smiling woman with long wavy brown hair)")
    print("  2. Resolved Object Aggregation (wearing oversized black cotton hoodie)")
    print("  3. Applied Relationship Chaining on Action clauses (standing next to red car in background)")
    print("  4. Composed Environment Integration (in a rain-soaked neon-lit alley)")
    print("  5. Structured overall Narrative Ordering and Phrase Fusion -> Done")

    try:
        compiled = compiler.compile_scene(scene)
        print("\n" + "=" * 80)
        print(" GENERATED NARRATIVE PROMPT ")
        print("-" * 80)
        print(compiled)
        print("=" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
