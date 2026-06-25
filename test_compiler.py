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
                "h1": {"type": "human", "subject": "urban_influencer",
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


class TestSubjects(unittest.TestCase):
    """Stage 2 — Subject resolution and overrides"""

    def setUp(self):
        self.c = PromptCompiler()

    def test_subject_defaults_applied(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "subject": "urban_influencer"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling", out)
        self.assertIn("long wavy brown hair", out)

    def test_subject_face_override(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "subject": "urban_influencer",
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


class TestHairOntology(unittest.TestCase):
    """Stage 7 — Hair Ontology Refactor tests."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_basic_hair_renders_correctly(self):
        """Old format still renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "dark brown", "length": "long", "style": "wavy"}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy dark brown hair", out)

    def test_hair_with_state_windblown(self):
        """State words render before structure."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "dark brown", "length": "long", "style": "wavy",
                                "state": ["windblown"]}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("windblown long wavy dark brown hair", out)

    def test_hair_wet_pool_scene(self):
        """Wet state for pool scene."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "dark brown", "length": "long",
                                "state": ["wet"]}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("wet long dark brown hair", out)

    def test_hair_backward_compat_old_format(self):
        """Old format with style key still works."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "brown", "length": "long", "style": "wavy"}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy brown hair", out)

    def test_hair_new_format_structure(self):
        """New format with structure/appearance."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "structure": {"length": "shoulder-length", "shape": "curly"},
                           "appearance": {"color": "auburn"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("shoulder-length curly auburn hair", out)

    def test_hair_new_format_arrangement(self):
        """Arrangement type renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "structure": {"length": "long", "shape": "straight"},
                           "appearance": {"color": "black"},
                           "arrangement": {"type": "ponytail"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("ponytail of long straight black hair", out)

    def test_hair_new_format_texture(self):
        """Texture renders in appearance."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "structure": {"length": "long", "shape": "wavy"},
                           "appearance": {"color": "blonde", "texture": "silky"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy blonde silky hair", out)

    def test_hair_multiple_states(self):
        """Multiple states render in order."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "structure": {"length": "long", "shape": "wavy"},
                           "appearance": {"color": "brown"},
                           "state": ["wet", "messy"]
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("wet messy long wavy brown hair", out)

    def test_hair_backward_compat_style_as_arrangement(self):
        """Old format style='ponytail' maps to arrangement."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "black", "length": "long", "style": "ponytail"}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("ponytail of long black hair", out)

    def test_hair_empty_state_renders_normally(self):
        """Empty state list doesn't affect output."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {"color": "brown", "length": "short", "style": "straight",
                                "state": []}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("short straight brown hair", out)

    def test_hair_color_balayage(self):
        """Balayage technique renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "color": {"base": "brown", "technique": "balayage", "secondary": "caramel"},
                           "structure": {"length": "long", "shape": "wavy"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy brown balayage with caramel hair", out)

    def test_hair_color_highlights(self):
        """Highlights technique renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "color": {"base": "dark brown", "technique": "highlights", "secondary": "honey blonde"},
                           "structure": {"length": "shoulder-length", "shape": "straight"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("shoulder-length straight honey blonde highlights on dark brown hair", out)

    def test_hair_color_fashion_vibrancy(self):
        """Fashion vibrancy prefix renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "color": {"base": "pink", "vibrancy": "pastel"},
                           "structure": {"length": "short", "shape": "straight"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("short straight pastel pink hair", out)

    def test_hair_arrangement_ponytail_position(self):
        """Arrangement with position renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "arrangement": {"type": "ponytail", "position": "high"},
                           "structure": {"length": "long", "shape": "straight"},
                           "color": {"base": "black"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("ponytail of long straight black hair", out)

    def test_hair_arrangement_braids_with_accessories(self):
        """Arrangement with accessories renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "arrangement": {
                               "primary": {"type": "box_braids", "length": "waist"},
                               "accessories": ["gold cuffs"]
                           },
                           "color": {"base": "black"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("box_braids of waist black hair with gold cuffs", out)

    def test_hair_cultural_locs(self):
        """Cultural style (locs) renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "cultural": {"style_type": "locs", "subtype": "traditional"},
                           "color": {"base": "black"},
                           "arrangement": {"primary": {"type": "locs", "length": "long"}}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("locs of long black hair", out)

    def test_hair_texture_strand_density(self):
        """Texture with strand and density (structural, not rendered)."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "texture": {"curl_pattern": "coily", "density": "thick", "strand": "fine"},
                           "color": {"base": "black"},
                           "arrangement": {"primary": {"type": "locs", "length": "waist"}}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        # curl_pattern is rendered, but density/strand are structural
        self.assertIn("locs of waist coily black hair", out)

    def test_hair_appearance_sheen_silky(self):
        """Appearance sheen renders when not 'natural'."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "appearance": {"sheen": "silky", "condition": "healthy"},
                           "color": {"base": "blonde"},
                           "structure": {"length": "long", "shape": "straight"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long straight blonde silky hair", out)

    def test_hair_backward_compat_partial_new_format(self):
        """Partial new format with structure/appearance still works."""
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hair": {
                           "structure": {"length": "long", "shape": "wavy"},
                           "appearance": {"color": "brown"}
                       }}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("long wavy brown hair", out)


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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
            "objects": {"h1": {"type": "human", "subject": "urban_influencer"}},
        }
        scene_objects = {
            "h1": SceneObject("h1", "human", {"type": "human", "subject": "urban_influencer"})
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

    def test_unknown_subject_does_not_crash(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"h1": {"type": "human", "gender": "man", "subject": "nonexistent_subject"}}
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
            "objects": {"h1": {"type": "human", "subject": "urban_influencer"}},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
        self.assertIn("wearing a black baseball cap", out_native)

    def test_composable_bathroom_ecs(self):
        # 1. Test ambient bathroom compilation (ECS Queries)
        scene_ambient = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "bathroom", "lighting": "steamy"},
            "objects": {
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
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
                "h1": {"type": "human", "subject": "urban_influencer"},
                "env_beach": {
                    "type": "environment",
                    "template_key": "Beach",
                    "weather": "stormy",
                    "lighting": "dark"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("on a stormy dimly lit beach", out)
        self.assertNotIn("beach in", out)
    def test_action_slot_descriptor_realization(self):
        # Test that relationship slot descriptors from actions.json compile correctly
        scene = {
            "camera": {"framing": "medium"},
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "subject": "urban_influencer"},
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
        
        self.assertIn("woman with smiling gently", out)
        self.assertIn("dark hair", out)
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

    def test_subway_tunnel_scene_recreation(self):
        scene = {
            "camera": {"framing": "medium"},
            "tone": "default",
            "render_profile": "cinematic",
            "style": "cinematic_teal_orange",
            "anchors": {
                "primary": "h1"
            },
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": "serious"
                    },
                    "Hair": {
                        "color": "blonde",
                        "style": "long, wavy"
                    },
                    "UpperBody": {
                        "owned_item_id": "dress_1"
                    }
                },
                "dress_1": {
                    "type": "clothing",
                    "template_key": "Dress",
                    "color": "green",
                    "style": "sleeveless",
                    "pattern": "white polka dots",
                    "material": "and a thin belt around her waist"
                },
                "env_tunnel": {
                    "type": "environment",
                    "template_key": "SubwayTunnel",
                    "location": "metallic walls and doors on both sides, featuring blurred motion lines suggesting speed or movement"
                }
            }
        }
        out = self.c.compile_scene(scene)
        
        self.assertIn("wearing a sleeveless green dress with white polka dots", out)
        self.assertIn("inside a subway tunnel with metallic walls and doors on both sides", out)
        self.assertIn("cinematic lighting, high contrast between teal and orange tones", out)


class TestPatterns(unittest.TestCase):
    """Test diverse pattern types and their prepositions across different templates."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_garment_pattern_floral(self):
        # 1. Floral pattern on a halter top
        desc = {
            "head": "halter top",
            "slots": {
                "color": { "position": "pre" },
                "pattern": { "position": "post", "prep": "featuring a floral print of" }
            }
        }
        ctx = {"color": "red", "pattern": "cherry blossoms"}
        self.assertEqual(
            safe_format(desc, ctx),
            "red halter top featuring a floral print of cherry blossoms"
        )

    def test_garment_pattern_plaid_preposition(self):
        # 2. Plaid pattern using "in a" preposition
        desc = {
            "head": "flannel shirt",
            "slots": {
                "pattern": { "position": "post", "prep": "in a" }
            }
        }
        ctx = {"pattern": "green and black plaid"}
        self.assertEqual(
            safe_format(desc, ctx),
            "flannel shirt in a green and black plaid"
        )

    def test_structural_pattern_checkered(self):
        # 3. Checkered pattern on structural objects (Wallpaper)
        desc = {
            "head": "wallpaper",
            "slots": {
                "pattern": { "position": "post", "prep": "with a" }
            }
        }
        ctx = {"pattern": "black and white checkered"}
        self.assertEqual(
            safe_format(desc, ctx),
            "wallpaper with a black and white checkered"
        )

    def test_abstract_pattern_paisley(self):
        # 4. Paisley pattern using "featuring"
        desc = {
            "head": "silk scarf",
            "slots": {
                "pattern": { "position": "post", "prep": "featuring" }
            }
        }
        ctx = {"pattern": "intricate blue paisley"}
        self.assertEqual(
            safe_format(desc, ctx),
            "silk scarf featuring intricate blue paisley"
        )


class TestCompositionApproach(unittest.TestCase):
    def setUp(self):
        self.c = PromptCompiler()

    def test_business_suit_full_resolution(self):
        # Full resolution of "business_suit" under full_body camera framing.
        scene = {
            "camera": {"framing": "full_body"},
            "tone": "default",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "man",
                    "attire": "business_suit"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("suit jacket", out)
        self.assertIn("suit pants", out)
        self.assertIn("oxford shoes", out)

    def test_attire_with_test_time_overrides(self):
        # Specific user overrides at test time (e.g. changing suit jacket color to navy and sneakers to red).
        scene = {
            "camera": {"framing": "full_body"},
            "tone": "default",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "attire": "tennis_uniform"
                },
                "polo_shirt_1": {
                    "color": "navy"
                },
                "sneakers_1": {
                    "color": "red"
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("navy polo shirt", out)
        self.assertIn("tennis skirt", out)
        self.assertIn("red sneakers", out)

    def test_attire_camera_framing_filtration(self):
        # Camera framing filtration: close_up hides the business suit, medium only renders the upper suit jacket.
        
        # 1. close_up framing
        scene_close_up = {
            "camera": {"framing": "close_up"},
            "tone": "default",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "man",
                    "attire": "business_suit"
                }
            }
        }
        out_close_up = self.c.compile_scene(scene_close_up)
        # In close_up, UpperBody, LowerBody, Feet are hidden (none of these should appear)
        self.assertNotIn("suit jacket", out_close_up)
        self.assertNotIn("suit pants", out_close_up)
        self.assertNotIn("oxford shoes", out_close_up)

        # 2. medium framing
        scene_medium = {
            "camera": {"framing": "medium"},
            "tone": "default",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "man",
                    "attire": "business_suit"
                }
            }
        }
        out_medium = self.c.compile_scene(scene_medium)
        # In medium, UpperBody is visible, but LowerBody and Feet are hidden
        self.assertIn("suit jacket", out_medium)
        self.assertNotIn("suit pants", out_medium)
        self.assertNotIn("oxford shoes", out_medium)


class TestNewEdgeCases(unittest.TestCase):
    """Edge cases: contradictory scenes, empty data, pronoun correctness, new presets."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_empty_relationships_array(self):
        scene = {
            "camera": {"framing": "medium"},
            "objects": {"h1": {"type": "human", "gender": "woman"}},
            "relationships": []
        }
        out = self.c.compile_scene(scene)
        self.assertIn("woman", out)

    def test_environment_with_missing_fields(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "man"},
                "env1": {"type": "environment", "template_key": "nonexistent_env"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIsInstance(out, str)

    def test_feet_visible_but_no_feet_data(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Face": {"expression": "smiling"}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("smiling", out)
        self.assertIn("woman", out)

    def test_invalid_tone_falls_back_to_default(self):
        scene = {
            "camera": {"framing": "close_up"},
            "tone": "nonexistent_tone",
            "objects": {
                "h1": {"type": "human", "gender": "man",
                       "Face": {"expression": "confident"}}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("man", out)

    def test_malformed_json_raises_value_error(self):
        import tempfile, os, json
        tmpdir = tempfile.mkdtemp()
        bad_path = os.path.join(tmpdir, "bad.json")
        with open(bad_path, "w") as f:
            f.write("{bad json content")
        try:
            compiler = PromptCompiler(data_dir=tmpdir)
            with self.assertRaises(ValueError) as ctx:
                compiler._load("bad.json", {})
            self.assertIn("Malformed JSON", str(ctx.exception))
        finally:
            os.remove(bad_path)
            os.rmdir(tmpdir)

    def test_holding_near_eye_male_pronoun(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "man"},
                "item1": {"type": "item", "template_key": "Sunglasses", "color": "black"}
            },
            "relationships": [
                {"type": "holding_near_eye", "actor": "h1", "object": "item1"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("his eye", out)

    def test_holding_near_eye_female_pronoun(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman"},
                "item1": {"type": "item", "template_key": "Sunglasses", "color": "black"}
            },
            "relationships": [
                {"type": "holding_near_eye", "actor": "h1", "object": "item1"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("her eye", out)

    def test_new_subject_professional_man(self):
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "h1": {"type": "human", "subject": "professional_man"},
                "suit_jacket_1": {"type": "clothing", "template_key": "SuitJacket", "color": "navy"},
                "suit_pants_1": {"type": "clothing", "template_key": "SuitPants", "color": "navy"},
                "oxford_shoes_1": {"type": "clothing", "template_key": "OxfordShoes", "color": "brown"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("man", out)
        self.assertIn("navy suit jacket", out)

    def test_new_subject_athletic_woman(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {
                "h1": {"type": "human", "subject": "athletic_woman"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("woman", out)

    def test_new_pose_arms_crossed_hides_hands(self):
        scene = {
            "camera": {"framing": "medium"},
            "pose": "arms_crossed",
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hands": {"owned_item_id": "ring_1"}},
                "ring_1": {"type": "accessory", "template_key": "Ring", "color": "gold"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("gold ring", out)

    def test_new_lighting_preset_soft(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "man"},
                "env1": {"type": "environment", "template_key": "cafe", "lighting": "soft"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("soft diffused", out)

    def test_new_weather_preset_foggy(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "man"},
                "env1": {"type": "environment", "template_key": "forest", "weather": "foggy"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("foggy", out)

    def test_person_user_gender_uses_they_pronoun(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "person"},
                "item1": {"type": "item", "template_key": "Sunglasses", "color": "black"}
            },
            "relationships": [
                {"type": "holding_near_eye", "actor": "h1", "object": "item1"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("their eye", out)


class TestBodySurfaceFeatures(unittest.TestCase):
    """Tests for body surface features (tattoos, scars, freckles, etc.)."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_tattoo_visible_no_clothing(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "UpperBody", "marking": "tattoo", "design": "a dragon on her forearm"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("dragon on her forearm", out)

    def test_tattoo_covered_by_clothing(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "subject": "professional_man",
                    "body_surface_features": [
                        {"location": "UpperBody", "marking": "tattoo", "design": "a tribal band on his arm"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("tribal band", out)

    def test_tattoo_covered_by_pose(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "hands_behind_back",
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "Hands", "marking": "tattoo", "design": "a small star on her hand"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("star on her hand", out)

    def test_freckles_visible_on_face(self):
        scene = {
            "camera": {"framing": "close_up"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "Face", "marking": "freckles", "design": "light freckles across her nose"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("light freckles across her nose", out)

    def test_scar_visible_on_leg_no_pants(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "determined"},
                    "body_surface_features": [
                        {"location": "LowerBody", "marking": "scar", "design": "a thin scar on her thigh"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("thin scar on her thigh", out)

    def test_scar_covered_by_pants(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "subject": "professional_man",
                    "body_surface_features": [
                        {"location": "LowerBody", "marking": "scar", "design": "a scar on his leg"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("scar on his leg", out)

    def test_multiple_features_partial_coverage(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "UpperBody": {"owned_item_id": "hoodie_1"},
                    "body_surface_features": [
                        {"location": "UpperBody", "marking": "tattoo", "design": "a rose on her shoulder"},
                        {"location": "LowerBody", "marking": "scar", "design": "a scrape on her knee"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("rose on her shoulder", out)
        self.assertIn("scrape on her knee", out)

    def test_close_up_hides_body_surface_on_lower_body(self):
        scene = {
            "camera": {"framing": "close_up"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "LowerBody", "marking": "tattoo", "design": "an ankle tattoo"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("ankle tattoo", out)

    def test_body_surface_feature_tag_in_cinematic(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "UpperBody", "marking": "tattoo", "design": "a vine tattoo on her arm"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("vine tattoo on her arm", out)

    def test_body_surface_feature_excluded_from_portrait(self):
        scene = {
            "camera": {"framing": "close_up"},
            "render_profile": "portrait",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "smiling"},
                    "body_surface_features": [
                        {"location": "Face", "marking": "freckles", "design": "freckles"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("freckles", out)

    def test_birthmark_visible(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {"expression": "thoughtful"},
                    "body_surface_features": [
                        {"location": "UpperBody", "marking": "birthmark", "design": "a small birthmark on her collarbone"}
                    ]
                }
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("small birthmark on her collarbone", out)

    def test_no_body_surface_features_component(self):
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "subject": "urban_influencer"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("with", out.split("on her")[0] if "on her" in out else "")


class TestPoseRendering(unittest.TestCase):
    """Pose is now rendered as text in the output."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_standing_pose_renders_text(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "standing",
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("standing", out)

    def test_sitting_pose_renders_text(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "sitting",
            "objects": {"h1": {"type": "human", "gender": "man"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("seated", out)

    def test_kneeling_pose_renders_text(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "kneeling",
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("kneeling", out)

    def test_arms_crossed_pose_renders_text(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "arms_crossed",
            "objects": {"h1": {"type": "human", "gender": "man"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("arms crossed", out)

    def test_leaning_pose_renders_text(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "leaning",
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("leaning", out)

    def test_no_pose_renders_nothing(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("standing", out)
        self.assertNotIn("seated", out)
        self.assertNotIn("kneeling", out)

    def test_pose_with_relationship(self):
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "standing",
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "woman"},
                "cup": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic"}
            },
            "relationships": [
                {"type": "holding", "actor": "h1", "object": "cup"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("standing", out)
        self.assertIn("holds", out)


class TestBodyConfig(unittest.TestCase):
    """Stage 8 — Body Configuration Ontology tests."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_body_config_head_tilt(self):
        """Head tilt renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"head": {"tilt": "slightly_left"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("tilted slightly to the left", out)

    def test_body_config_head_turn(self):
        """Head turn renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"head": {"turn": "away_from_camera"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("turned away from the camera", out)

    def test_body_config_gaze_direction(self):
        """Gaze direction renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"gaze": {"direction": "down"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("looking downward", out)

    def test_body_config_gaze_target(self):
        """Gaze with target renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"gaze": {"direction": "toward_target", "target": "phone"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("looking at phone", out)

    def test_body_config_arms_crossed(self):
        """Arms crossed renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"arms": {"left": "crossed", "right": "crossed"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("arms crossed", out)

    def test_body_config_arms_behind_back_hides_hands(self):
        """Arms behind back hides Hands zone."""
        scene = {
            "camera": {"framing": "medium"},
            "render_profile": "character_sheet",
            "body_config": {
                "h1": {"arms": {"left": "behind_back", "right": "behind_back"}}
            },
            "objects": {
                "h1": {"type": "human", "gender": "woman",
                       "Hands": {"owned_item_id": "ring"}},
                "ring": {"type": "accessory", "template_key": "Ring", "color": "gold"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("gold ring", out)
        self.assertIn("hands clasped behind their back", out)

    def test_body_config_legs_bent(self):
        """Legs bent renders correctly."""
        scene = {
            "camera": {"framing": "full_body"},
            "body_config": {
                "h1": {"legs": {"position": "bent"}}
            },
            "objects": {"h1": {"type": "human", "gender": "man"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("legs bent", out)

    def test_body_config_torso_lean(self):
        """Torso lean renders correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"torso": {"lean": "forward"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("leaning forward", out)

    def test_body_config_composable(self):
        """Multiple body config parts compose correctly."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {
                    "head": {"tilt": "slightly_left"},
                    "arms": {"left": "crossed", "right": "crossed"},
                    "gaze": {"direction": "down"}
                }
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        self.assertIn("tilted slightly to the left", out)
        self.assertIn("arms crossed", out)
        self.assertIn("looking downward", out)

    def test_body_config_overrides_pose(self):
        """Body config overrides scene-level pose."""
        scene = {
            "camera": {"framing": "full_body"},
            "pose": "standing",
            "body_config": {
                "h1": {"legs": {"position": "bent"}}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        # Body config should override pose
        self.assertIn("legs bent", out)

    def test_body_config_empty_renders_nothing(self):
        """Empty body config renders nothing."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {}
            },
            "objects": {"h1": {"type": "human", "gender": "woman"}}
        }
        out = self.c.compile_scene(scene)
        # Should not have any body config text
        self.assertNotIn("tilted", out)
        self.assertNotIn("looking", out)
        self.assertNotIn("arms", out)
        self.assertNotIn("legs", out)
        self.assertNotIn("leaning", out)

    def test_body_config_multi_character(self):
        """Multi-character scenes have independent body configs."""
        scene = {
            "camera": {"framing": "medium"},
            "body_config": {
                "h1": {"arms": {"left": "crossed", "right": "crossed"}},
                "h2": {"gaze": {"direction": "down"}}
            },
            "objects": {
                "h1": {"type": "human", "gender": "woman"},
                "h2": {"type": "human", "gender": "man"}
            }
        }
        out = self.c.compile_scene(scene)
        self.assertIn("arms crossed", out)
        self.assertIn("looking downward", out)


class TestEnvironmentAnchors(unittest.TestCase):
    """Environment anchors allow relationships to target objects within environments."""

    def setUp(self):
        self.c = PromptCompiler()

    def test_anchor_dot_notation_resolves(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "balcony"},
            "objects": {
                "h1": {"type": "human", "gender": "woman"}
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "balcony.railing"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("leaning", out)
        self.assertIn("railing", out)

    def test_anchor_fixture_created(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "balcony"},
            "objects": {
                "h1": {"type": "human", "gender": "man"}
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "balcony.railing"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("railing", out)

    def test_anchor_invalid_target_ignored(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "balcony"},
            "objects": {
                "h1": {"type": "human", "gender": "woman"}
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "balcony.nonexistent"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("nonexistent", out)

    def test_beach_anchor_sit_on_sand(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "beach"},
            "objects": {
                "h1": {"type": "human", "gender": "woman"}
            },
            "relationships": [
                {"type": "sitting", "actor": "h1"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("sits", out)

    def test_anchor_and_relationship_chained(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "cafe"},
            "objects": {
                "h1": {"type": "human", "gender": "man"},
                "cup": {"type": "drink", "template_key": "CoffeeCup", "material": "ceramic"}
            },
            "relationships": [
                {"type": "sitting", "actor": "h1"},
                {"type": "holding", "actor": "h1", "object": "cup"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("sits", out)
        self.assertIn("holding", out)

    def test_anchor_without_environment_ignored(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "objects": {
                "h1": {"type": "human", "gender": "woman"}
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "balcony.railing"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertNotIn("railing", out)

    def test_anchor_actor_resolves(self):
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",
            "environment": {"type": "office"},
            "objects": {
                "h1": {"type": "human", "gender": "man"}
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "office.window"}
            ]
        }
        out = self.c.compile_scene(scene)
        self.assertIn("leaning", out)
        self.assertIn("window", out)
