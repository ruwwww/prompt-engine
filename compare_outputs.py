"""Side-by-side comparison of old compiler vs new assembler outputs."""
import json
import sys
sys.path.insert(0, ".")

from compiler import PromptCompiler
from assembler import Assembler

compiler = PromptCompiler()
assembler = Assembler()


def compare(label, scene):
    old = compiler.compile_scene(scene, strict=False)
    new = assembler.assemble(scene)
    match = old.strip() == new.strip()
    status = "MATCH" if match else "DIFF"
    print(f"\n{'='*60}")
    print(f"[{status}] {label}")
    print(f"  OLD: {old}")
    print(f"  NEW: {new}")
    return match


results = []

# Test 1: Orc basic (full_body)
results.append(compare("Orc basic (full_body)", {
    "camera": {"framing": "full_body"},
    "objects": {
        "orc1": {
            "type": "creature",
            "subject": "orc_warrior",
            "Face": {"expression": "snarling"},
            "Tusks": {"size": "large", "material": "ivory"},
        }
    }
}))

# Test 2: Elf basic (medium)
results.append(compare("Elf basic (medium)", {
    "camera": {"framing": "medium"},
    "objects": {
        "elf1": {
            "type": "creature",
            "subject": "elf_archer",
            "Face": {"expression": "focused"},
            "Ears": {"shape": "pointed", "length": "long"},
        }
    }
}))

# Test 3: Human basic (close_up)
results.append(compare("Human basic (close_up)", {
    "camera": {"framing": "close_up"},
    "objects": {
        "h1": {
            "type": "human",
            "Face": {"expression": "smiling"},
            "Hair": {"color": "brown", "length": "long", "style": "wavy"},
        }
    }
}))

# Test 4: Human subject defaults
results.append(compare("Human subject defaults", {
    "camera": {"framing": "full_body"},
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
        }
    }
}))

# Test 5: Close up hides feet
results.append(compare("Close up hides feet", {
    "camera": {"framing": "close_up"},
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
            "Feet": {"style": "sneakers", "color": "white"},
        }
    }
}))

# Test 6: Orc with clothing
results.append(compare("Orc with clothing (full_body)", {
    "camera": {"framing": "full_body"},
    "objects": {
        "orc1": {
            "type": "creature",
            "subject": "orc_warrior",
            "Face": {"expression": "snarling"},
            "Tusks": {"size": "large", "material": "ivory"},
            "UpperBody": {"type": "clothing", "template_key": "Chainmail", "material": "iron", "color": "steel_gray"},
            "LowerBody": {"type": "clothing", "template_key": "LeatherPants", "material": "leather", "color": "brown"},
            "Feet": {"type": "clothing", "template_key": "IronBoots", "material": "iron", "color": "dark_gray"},
        }
    }
}))

# Test 7: Environment scene
results.append(compare("Environment scene", {
    "camera": {"framing": "medium"},
    "environment": {"type": "cozy_bedroom", "lighting": "warm_lamp", "weather": "clear"},
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
        }
    }
}))

# Test 8: Style overlay
results.append(compare("Style overlay", {
    "camera": {"framing": "medium"},
    "style": "editorial",
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
        }
    }
}))

# Test 9: Body config
results.append(compare("Body config", {
    "camera": {"framing": "full_body"},
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
        }
    },
    "body_config": {
        "h1": {
            "head": {"tilt": "slightly_left"},
            "gaze": {"direction": "toward_target", "target": "phone"},
        }
    }
}))

# Test 10: Attire bundle
results.append(compare("Attire bundle", {
    "camera": {"framing": "full_body"},
    "objects": {
        "h1": {
            "type": "human",
            "attire": "business_suit",
        }
    }
}))

# Test 11: Relationship
results.append(compare("Relationship (holding)", {
    "camera": {"framing": "full_body"},
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
        },
        "phone1": {
            "type": "item",
            "template_key": "Smartphone",
            "color": "black",
        },
    },
    "relationships": [
        {"type": "holding", "actor": "h1", "object": "phone1"}
    ]
}))

# Test 12: Full composition
results.append(compare("Full composition", {
    "camera": {"framing": "full_body"},
    "composition": {"type": "rule_of_thirds"},
    "style": "cinematic_teal_orange",
    "objects": {
        "h1": {
            "type": "human",
            "subject": "urban_influencer",
            "UpperBody": {"type": "clothing", "template_key": "Tshirt", "color": "red"},
        }
    }
}))

# Summary
print(f"\n{'='*60}")
matched = sum(results)
total = len(results)
print(f"SUMMARY: {matched}/{total} matched")
if matched < total:
    print("DIFFERENCES REMAIN - investigate above")
