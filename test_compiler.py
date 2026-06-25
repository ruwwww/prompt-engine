"""
test_compiler.py — Full regression + edge-case test suite
Covers Stages 1-6 + Architecture Polish
"""
import unittest
from compiler import PromptCompiler, safe_format

class TestSafeFormat(unittest.TestCase):
    """Phase 1 — safe_format utility"""

    def test_all_keys_present(self):
        self.assertEqual(safe_format("{fit} {color} {material} hoodie",
                                     {"fit": "oversized", "color": "black", "material": "cotton"}),
                         "oversized black cotton hoodie")

    def test_missing_keys_collapse(self):
        self.assertEqual(safe_format("{fit} {color} {material} hoodie", {"color": "red"}),
                         "red hoodie")

    def test_no_double_spaces(self):
        result = safe_format("{a} {b} word", {"b": "some"})
        self.assertNotIn("  ", result)


class TestVisibility(unittest.TestCase):
    """Stage 1-2 — Camera + Pose visibility"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_close_up_hides_feet(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Face": {"expression": "smiling"},
                       "Hair": {"color": "brown", "length": "long"},
                       "Feet": {"owned_item_id": "s1"}},
                "s1": {"type": "clothing", "template_key": "Shoes", "color": "black"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling", out)
        self.assertIn("long", out)
        self.assertNotIn("shoes", out)
        self.assertNotIn("black", out)

    def test_full_body_shows_feet(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Feet": {"owned_item_id": "s1"}},
                "s1": {"type": "clothing", "template_key": "Shoes", "color": "white"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("white", out)

    def test_pose_hides_hands(self):
        scene = {
            "camera": {"framing": "medium"},
            "pose": "hands_behind_back",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer",
                       "Face": {"expression": "grinning"}},
                "ring_1": {"type": "accessory", "template_key": "Ring", "material": "silver"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("grinning woman", out)
        self.assertNotIn("smiling woman", out)
        self.assertNotIn("silver ring", out)

    def test_pose_sitting_hides_feet(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "sitting",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Feet": {"owned_item_id": "s1"}},
                "s1": {"type": "clothing", "template_key": "Shoes", "color": "white"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("shoes", out)


class TestPersonas(unittest.TestCase):
    """Stage 2 — Persona resolution and overrides"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_persona_defaults_applied(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "persona": "urban_influencer"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling", out)
        self.assertIn("long wavy brown hair", out)

    def test_persona_face_override(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "persona": "urban_influencer",
                                "Face": {"expression": "laughing"}}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("laughing", out)
        self.assertNotIn("smiling", out)


class TestAttributeComposition(unittest.TestCase):
    """Stage 2 — Render template attribute composition"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_hair_renders_in_order(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "gender": "woman",
                                "Hair": {"length": "long", "style": "wavy", "color": "brown"}}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy brown hair", out)

    def test_clothing_aggregation_multiple(self):
        """Multiple clothing items appear joined with 'wearing'."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "UpperBody": {"owned_item_id": "hoodie_1"},
                       "LowerBody": {"owned_item_id": "pants_1"}},
                "hoodie_1": {"type": "clothing", "template_key": "Hoodie",
                              "fit": "oversized", "color": "black", "material": "cotton"},
                "pants_1": {"type": "clothing", "template_key": "CargoPants",
                             "fit": "baggy", "color": "olive"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("wearing", out)
        self.assertIn("hoodie", out)
        self.assertIn("cargo pants", out)


class TestRelationships(unittest.TestCase):
    """Stage 4 — Actions, interactions, variants, visibility"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_holding_drink_variant(self):
        scene = {
            "camera": {"framing": "medium"},
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "c1": {"type": "drink", "template_key": "CoffeeCup",
                        "material": "ceramic", "color": "white"},
            },
            "relationships": [{"type": "holding", "actor": "h1", "object": "c1"}]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("holding a cup of a ceramic coffee cup", out)

    def test_holding_occluded_by_pose(self):
        scene = {
            "camera": {"framing": "medium"},
            "pose": "hands_behind_back",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "c1": {"type": "drink", "template_key": "CoffeeCup",
                        "material": "ceramic", "color": "white"},
            },
            "relationships": [{"type": "holding", "actor": "h1", "object": "c1"}]
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("holding", out)

    def test_invalid_relationship_type_skipped(self):
        """Wrong type on relationship role — silently skipped."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "car1": {"type": "vehicle", "template_key": "Car", "color": "red"},
            },
            "relationships": [{"type": "holding", "actor": "h1", "object": "car1"}]  # vehicle not allowed for holding
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("holding", out)


class TestSpatialAndScene(unittest.TestCase):
    """Stage 5 — Spatial relationships, placements, environment"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_spatial_relationship_rendered(self):
        scene = {
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
            "relationships": [{"type": "standing_next_to", "subject": "h1", "target": "car_1"}]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("in a rain-soaked neon-lit alley", out)
        self.assertIn("stands next to a red car in background", out)
        self.assertIn("shot in cinematic style", out)


class TestRenderProfiles(unittest.TestCase):
    """Stage 3 — Emit profiles, tag filtering, budgets"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_portrait_excludes_clothing(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "portrait",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "hoodie_1": {"type": "clothing", "template_key": "Hoodie",
                              "fit": "oversized", "color": "black", "material": "cotton"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling", out)
        self.assertNotIn("hoodie", out)

    def test_fashion_excludes_emotion(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "fashion",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "hoodie_1": {"type": "clothing", "template_key": "Hoodie",
                              "fit": "oversized", "color": "black", "material": "cotton"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("smiling woman", out)
        self.assertIn("hoodie", out)


class TestValidationSystem(unittest.TestCase):
    """Phase 3 — ValidationSystem"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_unknown_relationship_type_flagged(self):
        from compiler import SceneObject
        scene = {
            "objects": {"h1": {"type": "human", "gender": "woman"}},
            "relationships": [{"type": "teleporting", "actor": "h1"}]
        }
        scene_objects = {
            "h1": SceneObject("h1", "human", {"type": "human", "gender": "woman"})
        }
        errors = self.c.validation_system.validate(scene, scene_objects)
        error_msgs = [e.message for e in errors]
        self.assertTrue(any("teleporting" in m for m in error_msgs))

    def test_missing_anchor_object_flagged(self):
        from compiler import SceneObject
        scene = {
            "objects": {"h1": {"type": "human", "gender": "woman"}},
            "anchors": {"primary": "nonexistent_object"},
        }
        scene_objects = {
            "h1": SceneObject("h1", "human", {"type": "human", "gender": "woman"})
        }
        errors = self.c.validation_system.validate(scene, scene_objects)
        self.assertTrue(any("nonexistent_object" in e.message for e in errors))

    def test_strict_mode_raises(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {"h1": {"type": "human", "gender": "woman"}},
            "anchors": {"primary": "ghost_obj"},
        }
        with self.assertRaises(ValueError):
            self.c.compile_scene(scene, strict=True)

    def test_clean_scene_no_errors(self):
        from compiler import SceneObject
        scene = {
            "objects": {"h1": {"type": "human", "persona": "urban_influencer"}},
        }
        scene_objects = {
            "h1": SceneObject("h1", "human", {"type": "human", "persona": "urban_influencer"})
        }
        errors = self.c.validation_system.validate(scene, scene_objects)
        hard = [e for e in errors if e.severity == "error"]
        self.assertEqual(hard, [])


class TestEdgeCases(unittest.TestCase):
    """Phase 3 — Edge cases that break naive compilers"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_empty_scene_returns_empty_string(self):
        out = self.c.compile_scene({"objects": {}})
        self.assertEqual(out, "")

    def test_scene_with_no_human_returns_empty(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {
                "c1": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic", "color": "white"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertEqual(out, "")

    def test_unknown_persona_does_not_crash(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "gender": "man", "persona": "nonexistent_persona"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("man", out)

    def test_missing_template_key_does_not_crash(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "UpperBody": {"owned_item_id": "mystery_item"}},
                "mystery_item": {"type": "clothing", "template_key": "NonExistentTemplate",
                                  "color": "purple"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIsInstance(out, str)   # should not crash

    def test_multiple_relationships_same_subject_chained(self):
        scene = {
            "camera": {"framing": "medium"},
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman"},
                "c1": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic", "color": "white"},
            },
            "relationships": [
                {"type": "holding", "actor": "h1", "object": "c1"},
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("holding", out)

    def test_environment_without_weather_does_not_crash(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "alley", "lighting": "neon"},
            "objects": {"h1": {"type": "human", "persona": "urban_influencer"}},
        }
        out = self.c.compile_scene(scene)
        self.assertIn("neon", out)


class TestMultiCharacter(unittest.TestCase):
    """Phase 4 — Multi-character scenes"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_two_humans_both_described(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                        "Face": {"expression": "smiling"},
                        "Hair": {"color": "brown", "length": "long", "style": "wavy"}},
                "h2": {"type": "human", "gender": "man",
                        "Face": {"expression": "serious"}},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("woman", out)
        self.assertIn("man", out)


class TestNarrativeMode(unittest.TestCase):
    """Phase 5 — Scene description narrative mode"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_scene_description_mode_produces_sentence(self):
        """The cinematic profile with scene_description mode should produce a sentence."""
        # Temporarily patch the profile to use scene_description mode
        original = self.c.render_system.profiles.get("cinematic", {}).copy()
        self.c.render_system.profiles["cinematic"]["narrative_mode"] = "scene_description"

        scene = {
            "camera": {"framing": "full_body"},
            "pose": "standing",
            "render_profile": "cinematic",
            "environment": {"type": "alley", "lighting": "neon", "weather": "rainy"},
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "car_1": {"type": "vehicle", "template_key": "Car", "color": "red"},
            },
            "relationships": [{"type": "standing_next_to", "subject": "h1", "target": "car_1"}]
        }
        out = self.c.compile_scene(scene)

        # Should be a proper sentence ending with period
        self.assertTrue(out.endswith("."), f"Expected sentence ending with '.', got: {out}")
        # Should start with A/An
        self.assertTrue(out.startswith("A ") or out.startswith("An "),
                        f"Expected sentence starting with 'A/An', got: {out}")
        # Finite verb instead of participle for subject
        self.assertIn("stands next to", out)

        # Restore
        self.c.render_system.profiles["cinematic"] = original


class TestNewFeatures(unittest.TestCase):
    """Stage 7 & 8 — Chaining, Style System, and Bug Fixes"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_style_system(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "portrait",
            "style": "editorial",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("editorial fashion photography", out)

    def test_relationship_chaining(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "woman"},
                "car_1": {"type": "vehicle", "template_key": "Car", "color": "blue"},
                "c1": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic", "color": "white"},
            },
            "relationships": [
                {"type": "holding", "actor": "h1", "object": "c1"},
                {"type": "inside", "subject": "h1", "container": "car_1"},
            ]
        }
        out = self.c.compile_scene(scene)
        # Should chain them with space: "sits inside a blue car holding a cup of a ceramic coffee cup"
        self.assertIn("sits inside a blue car holding a cup of a ceramic coffee cup", out)

    def test_multi_character_expression_preservation(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                        "Face": {"expression": "smiling"}},
                "h2": {"type": "human", "gender": "man",
                        "Face": {"expression": "serious"}},
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling woman", out)
        self.assertIn("serious man", out)

    def test_eyes_and_headwear(self):
        scene = {
            "camera": {"framing": "close_up"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Eyes": {"color": "green"},
                    "Headwear": {"owned_item_id": "sunglasses_1"},
                },
                "sunglasses_1": {
                    "type": "accessory",
                    "template_key": "Sunglasses",
                    "style": "aviator",
                    "color": "black",
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("green eyes", out)
        self.assertIn("black aviator sunglasses", out)

        # Test native headwear
        scene_native = {
            "camera": {"framing": "close_up"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Headwear": {"color": "black", "style": "baseball cap"},
                }
            }
        }
        out_native = self.c.compile_scene(scene_native)
        self.assertIn("wearing black baseball cap", out_native)

    def test_composable_bathroom_ecs(self):
        # 1. Test ambient bathroom compilation (ECS Queries)
        scene_ambient = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "bathroom", "lighting": "steamy"},
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "tub_1": {
                    "type": "fixture",
                    "template_key": "Bathtub",
                    "color": "white",
                    "material": "porcelain",
                    "style": "clawfoot"
                },
                "mirror_1": {
                    "type": "fixture",
                    "template_key": "Mirror",
                    "style": "vintage"
                }
            }
        }
        out_ambient = self.c.compile_scene(scene_ambient)
        # Should include ambient fixtures in environment description
        self.assertIn("inside a sunny steamy bathroom featuring a white porcelain clawfoot bathtub and a vintage mirror", out_ambient)

        # 2. Test interactive bathroom: occupied fixture is excluded from ambient environment description
        scene_interactive = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "bathroom", "lighting": "steamy"},
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "tub_1": {
                    "type": "fixture",
                    "template_key": "Bathtub",
                    "color": "white",
                    "material": "porcelain",
                    "style": "clawfoot"
                },
                "mirror_1": {
                    "type": "fixture",
                    "template_key": "Mirror",
                    "style": "vintage"
                }
            },
            "relationships": [
                {"type": "soaking_in", "actor": "h1", "object": "tub_1"}
            ]
        }
        out_interactive = self.c.compile_scene(scene_interactive)
        # The tub is occupied, so it should only feature the mirror in the environment description,
        # while the tub is described in the relationship clause.
        self.assertIn("soaks in a white porcelain clawfoot bathtub", out_interactive)
        self.assertIn("inside a sunny steamy bathroom featuring a vintage mirror", out_interactive)
        self.assertNotIn("bathtub and a vintage mirror", out_interactive)

    def test_beach_oop_ecs(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "env_beach": {
                    "type": "environment",
                    "template_key": "Beach",
                    "geolocation": "Malibu",
                    "weather": "breezy",
                    "lighting": "golden_hour"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("on a breezy golden-hour beach in Malibu", out)

    def test_forest_oop_ecs(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "env_forest": {
                    "type": "environment",
                    "template_key": "Forest",
                    "location": "the Pacific Northwest",
                    "weather": "foggy",
                    "lighting": "sunlight"
                },
                "tree_1": {
                    "type": "fixture",
                    "template_key": "Tree",
                    "color": "lush green",
                    "species": "pine"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("in a foggy sunlight forest in the Pacific Northwest featuring a lush green pine tree", out)


class TestSlotDescriptors(unittest.TestCase):
    """Test the experimental slot descriptor format and realizer."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_slot_descriptor_all_slots(self):
        # Beach with all slots filled
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "env_beach": {
                    "type": "environment",
                    "template_key": "Beach",
                    "geolocation": "Hawaii",
                    "weather": "sunny",
                    "lighting": "bright"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("on a sunny bright beach in Hawaii", out)

    def test_slot_descriptor_missing_optional_slots(self):
        # Beach with weather and lighting missing
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "env_beach": {
                    "type": "environment",
                    "template_key": "Beach",
                    "geolocation": "Hawaii"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("on a beach in Hawaii", out)

    def test_slot_descriptor_missing_geolocation(self):
        # Beach with missing geolocation (omits "in" preposition)
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "env_beach": {
                    "type": "environment",
                    "template_key": "Beach",
                    "weather": "stormy",
                    "lighting": "dark"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("on a stormy dark beach", out)
        self.assertNotIn("beach in", out)
    def test_action_slot_descriptor_realization(self):
        # Test that relationship slot descriptors from actions.json compile correctly
        scene = {
            "camera": {"framing": "medium"},
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "persona": "urban_influencer"},
                "c1": {"type": "drink", "template_key": "CoffeeCup",
                        "material": "ceramic", "color": "white"},
            },
            "relationships": [{"type": "holding", "actor": "h1", "object": "c1"}]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("holding a cup of a ceramic coffee cup", out)

    def test_dynamic_article_adjustment(self):
        # Directly test safe_format handles a/an adjustments
        from compiler import safe_format
        # a -> an before vowels
        self.assertEqual(safe_format("a {color} hoodie", {"color": "orange"}), "an orange hoodie")
        self.assertEqual(safe_format("A {color} apple", {"color": "emerald"}), "An emerald apple")
        # an -> a before consonants
        self.assertEqual(safe_format("an {color} car", {"color": "red"}), "a red car")
        self.assertEqual(safe_format("An {color} cap", {"color": "blue"}), "A blue cap")

    def test_adjective_ordering(self):
        from compiler import safe_format
        
        # Define a slot descriptor for a hoodie
        hoodie_desc = {
            "head": "hoodie",
            "slots": {
                "color": { "position": "pre" },     # Rank 6 (color)
                "material": { "position": "pre" },  # Rank 8 (material)
                "fit": { "position": "pre" }         # Rank 3 (fit)
            }
        }
        
        # Test default sorting: fit (3) -> color (6) -> material (8)
        ctx = {"color": "black", "material": "cotton", "fit": "oversized"}
        self.assertEqual(
            safe_format(hoodie_desc, ctx),
            "oversized black cotton hoodie"
        )
        
        # Test explicit rank overrides: making material rank 1
        hoodie_override_desc = {
            "head": "hoodie",
            "slots": {
                "color": { "position": "pre" },
                "material": { "position": "pre", "rank": 1 },
                "fit": { "position": "pre" }
            }
        }
        self.assertEqual(
            safe_format(hoodie_override_desc, ctx),
            "cotton oversized black hoodie"
        )

    def test_noun_pluralization_and_agreement(self):
        from compiler import safe_format
        
        # 1. Test noun pluralization rule (plural suffix)
        cup_descriptor = {
            "head": "cup",
            "plural": { "suffix": "s" },
            "slots": {
                "color": { "position": "pre" }
            }
        }
        self.assertEqual(
            safe_format(cup_descriptor, {"color": "white", "_plural_self": True}),
            "white cups"
        )

        # 2. Test irregular noun pluralization
        man_descriptor = {
            "head": "man",
            "plural": { "irregular": "men" },
            "slots": {
                "style": { "position": "pre" }
            }
        }
        self.assertEqual(
            safe_format(man_descriptor, {"style": "handsome", "_plural_self": True}),
            "handsome men"
        )

        # 3. Test verb agreement (singular/plural heads)
        holding_descriptor = {
            "head": {
                "singular": "is holding",
                "plural": "are holding",
                "agreement_with": "actor"
            },
            "slots": {
                "actor": { "position": "pre" },
                "object": { "position": "post" }
            }
        }
        self.assertEqual(
            safe_format(holding_descriptor, {"actor": "she", "object": "a cup", "_plural_actor": False}),
            "she is holding a cup"
        )
        self.assertEqual(
            safe_format(holding_descriptor, {"actor": "they", "object": "cups", "_plural_actor": True}),
            "they are holding cups"
        )

    def test_contextual_pronouns_and_anaphora(self):
        # Test pronoun resolution in compile_scene
        scene = {
            "camera": {"framing": "medium"},
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman", "Face": {"expression": "smiling"}},
                "h2": {"type": "human", "gender": "man", "Face": {"expression": "serious"}},
                "c1": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic"}
            },
            "relationships": [
                # h1 holding c1
                {"type": "holding", "actor": "h1", "object": "c1"},
                # h2 hugging h1
                {"type": "hugging", "subject1": "h2", "subject2": "h1"},
            ]
        }
        out = self.c.compile_scene(scene)
        
        # In fact_chain, h1 (woman) and h2 (man) are introduced first.
        # h1 holding c1: c1 is first mentioned -> "holding a cup of a ceramic coffee cup"
        # h2 hugging h1: hugging clause -> "hugging her" (since h1 is target and already mentioned)
        self.assertIn("holding a cup of a ceramic coffee cup", out)
        self.assertIn("hugging her", out)
        self.assertNotIn("hugging smiling woman", out)

    def test_linguistic_tone_controllers(self):
        # 1. Test template-level head tone mapping
        forest_poetic_descriptor = {
            "head": {
                "default": "forest",
                "poetic": "woodlands"
            },
            "slots": {
                "weather": { "position": "pre" }
            }
        }
        # default tone
        self.assertEqual(
            safe_format(forest_poetic_descriptor, {"weather": "foggy", "_tone": "default"}),
            "foggy forest"
        )
        # poetic tone
        self.assertEqual(
            safe_format(forest_poetic_descriptor, {"weather": "foggy", "_tone": "poetic"}),
            "foggy woodlands"
        )

        # 2. Test value-level attribute tone mapping (passed in components)
        scene = {
            "camera": {"framing": "medium"},
            "tone": "vivid",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": {
                            "default": "smiling",
                            "vivid": "beaming",
                            "concise": "calm"
                        }
                    }
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("beaming woman", out)

        # 3. Test concise tone (should resolve to concise mapping)
        scene_concise = {
            "camera": {"framing": "medium"},
            "tone": "concise",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": {
                            "default": "smiling",
                            "vivid": "beaming",
                            "concise": "calm"
                        }
                    }
                }
            }
        }
        out_concise = self.c.compile_scene(scene_concise)
        self.assertIn("calm woman", out_concise)

    def test_tennis_court_scene_recreation(self):
        scene = {
            "camera": {"framing": "medium"},
            "tone": "default",
            "render_profile": "cinematic",
            "style": "photorealistic",
            "anchors": {
                "primary": "h1"
            },
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": "smiling gently",
                        "makeup": "soft"
                    },
                    "Hair": {
                        "color": "dark",
                        "style": "pulled back into a high ponytail"
                    },
                    "Hands": {
                        "owned_item_id": "racket_1"
                    },
                    "UpperBody": {
                        "owned_item_id": "dress_1"
                    },
                    "Headwear": {
                        "owned_item_id": "earrings_1"
                    }
                },
                "earrings_1": {
                    "type": "clothing",
                    "template_key": "Earrings",
                    "style": "hoop"
                },
                "dress_1": {
                    "type": "clothing",
                    "template_key": "Dress",
                    "style": "one-shoulder pale yellow athletic dress with a fitted bodice and a pleated skirt that has a sheer mesh hem"
                },
                "racket_1": {
                    "type": "item",
                    "template_key": "Racket",
                    "color": "white and yellow",
                    "style": "tennis"
                },
                "env_court": {
                    "type": "environment",
                    "template_key": "TennisCourt",
                    "material": "clay",
                    "lighting": "natural daylight",
                    "location": "white boundary lines visible on the reddish-brown ground"
                }
            },
            "relationships": [
                {"type": "holding", "actor": "h1", "object": "racket_1"}
            ]
        }
        out = self.c.compile_scene(scene)
        
        self.assertIn("smiling gently woman", out)
        self.assertIn("wearing hoop earrings and one-shoulder pale yellow athletic dress", out)
        self.assertIn("holds a white and yellow tennis racket", out)
        self.assertIn("on a clay tennis court outdoors with white boundary lines", out)
        self.assertIn("photorealistic", out)

    def test_sushi_scene_recreation(self):
        scene = {
            "camera": {"framing": "medium"},
            "tone": "default",
            "render_profile": "cinematic",
            "style": "cinematic",
            "anchors": {
                "primary": "h1"
            },
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": "puckering her lips in a playful expression with her eyes closed or squinting slightly"
                    },
                    "Hair": {
                        "color": "dark brown",
                        "style": "pulled back into a loose, textured bun and long side-swept bangs framing her face"
                    },
                    "Hands": {
                        "owned_item_id": "chopsticks_1"
                    },
                    "UpperBody": {
                        "owned_item_id": "top_1"
                    }
                },
                "top_1": {
                    "type": "clothing",
                    "template_key": "HalterTop",
                    "color": "vibrant red",
                    "style": "halter-neck",
                    "material": "featuring delicate pink floral embroidery on the chest and green leaves"
                },
                "chopsticks_1": {
                    "type": "clothing",
                    "template_key": "Chopsticks",
                    "material": "wooden",
                    "plural": True,
                    "holding_item_id": "sushi_1"
                },
                "sushi_1": {
                    "type": "item",
                    "template_key": "SushiRoll",
                    "style": "rice, nori, avocado, and crab or fish filling"
                },
                "env_restaurant": {
                    "type": "environment",
                    "template_key": "RestaurantInterior",
                    "location": "warm ambient lighting, featuring a blurred wall art background depicting a large red sun and dark mountain silhouettes"
                }
            },
            "relationships": [
                {"type": "holding_near_eye", "actor": "h1", "object": "chopsticks_1"}
            ]
        }
        out = self.c.compile_scene(scene)
        
        self.assertIn("halter-neck vibrant red top featuring delicate pink floral embroidery", out)
        self.assertIn("wooden chopsticks holding a sushi roll containing rice, nori, avocado, and crab or fish filling", out)
        self.assertIn("inside a restaurant interior with warm ambient lighting", out)
        self.assertIn("holds wooden chopsticks holding a sushi roll containing rice, nori, avocado, and crab or fish filling near her eye", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
