"""
test_refactor.py — End-to-end smoke tests for the spatial ontology refactor.

Run: pytest test_refactor.py -v
"""

import json
import unittest
from compiler import PromptCompiler, Assembler, derive_preposition


class TestSmoke(unittest.TestCase):
    """Five end-to-end smoke test cases from the refactoring specification."""

    def setUp(self):
        self.c = PromptCompiler()

    def _run(self, scene: dict) -> str:
        return self.c.assemble(scene, output_format="legacy")

    def test_enclosed_environment_single_subject_with_interaction(self):
        """Test Case 1: Enclosed environment, single subject with fixture interaction."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman", "subject": "adult"},
                "cafe": {"type": "environment", "template_key": "cafe"},
                "counter": {"type": "fixture", "template_key": "counter"},
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "counter"}
            ],
        }
        out = self._run(scene)
        # Lead contains environment
        self.assertIn("cafe", out)
        # Preposition is "inside" for enclosed
        self.assertIn("inside a cafe", out)
        # No "featuring" anywhere
        self.assertNotIn("featuring", out.lower())
        # Action clause shows interaction
        self.assertIn("leaning", out.lower() or "leans", out.lower())

    def test_open_environment_subject_on_ground(self):
        """Test Case 2: Open environment, subject on ground surface."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "woman", "subject": "adult"},
                "beach": {"type": "environment", "template_key": "beach"},
                "towel": {"type": "fixture", "template_key": "towel"},
            },
            "relationships": [
                {"type": "sitting", "actor": "h1", "target": "towel"}
            ],
        }
        out = self._run(scene)
        # Preposition derived from containment=open, normal=up
        self.assertIn("on a beach", out)
        # Action clause shows interaction
        self.assertIn("sitting", out.lower())
        # No unbound fixtures
        self.assertNotIn("featuring", out.lower())

    def test_transitional_environment_balcony(self):
        """Test Case 3: Transitional environment (balcony)."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "man", "subject": "adult"},
                "balcony": {"type": "environment", "template_key": "balcony"},
                "railing": {"type": "fixture", "template_key": "railing"},
            },
            "relationships": [
                {"type": "leaning_on", "actor": "h1", "target": "railing"}
            ],
        }
        out = self._run(scene)
        # Preposition "at" for transitional
        self.assertIn("at a balcony", out)
        # No unbound fixtures
        self.assertNotIn("featuring", out.lower())

    def test_no_relationships_subject_only(self):
        """Test Case 4: No relationships (subject only, no interactions)."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "character_sheet",
            "objects": {
                "h1": {"type": "human", "gender": "man", "subject": "adult"},
                "cafe": {"type": "environment", "template_key": "cafe"},
            },
        }
        out = self._run(scene)
        # Environment appears with correct preposition
        self.assertIn("inside a cafe", out)
        # No fixture names
        self.assertNotIn("counter", out)
        self.assertNotIn("featuring", out.lower())

    def test_narrative_mode_finite_verb(self):
        """Test Case 5: Narrative mode produces finite verb form."""
        scene = {
            "camera": {"framing": "full_body"},
            "render_profile": "cinematic",  # Uses narrative mode
            "objects": {
                "h1": {"type": "human", "gender": "man", "subject": "adult"},
                "office": {"type": "environment", "template_key": "office"},
                "desk": {"type": "fixture", "template_key": "desk"},
            },
            "relationships": [
                {"type": "sitting", "actor": "h1", "target": "desk"}
            ],
        }
        out = self._run(scene)
        # Finite verb "sits" not participial "sitting"
        self.assertIn("sits", out.lower())
        # Office is enclosed → preposition is "inside"
        self.assertIn("inside an office", out.lower())


class TestDerivePreposition(unittest.TestCase):
    """Unit tests for derive_preposition()."""

    def setUp(self):
        with open("data/spatial_prepositions.json") as f:
            self.sp = json.load(f)

    def test_enclosed_returns_inside(self):
        env = {"volume": {"containment": "enclosed"}, "primary_surface": {"normal": "up"}}
        self.assertEqual(derive_preposition(env, self.sp), "inside")

    def test_open_normal_up_returns_on(self):
        env = {"volume": {"containment": "open"}, "primary_surface": {"normal": "up"}}
        self.assertEqual(derive_preposition(env, self.sp), "on")

    def test_open_normal_lateral_returns_against(self):
        env = {"volume": {"containment": "open"}, "primary_surface": {"normal": "lateral"}}
        self.assertEqual(derive_preposition(env, self.sp), "against")

    def test_transitional_returns_at(self):
        env = {"volume": {"containment": "transitional"}, "primary_surface": {"normal": "up"}}
        self.assertEqual(derive_preposition(env, self.sp), "at")

    def test_impossible_boundary_absent(self):
        env = {"volume": {"containment": "impossible", "boundary": "absent"}, "primary_surface": {"normal": "null"}}
        self.assertEqual(derive_preposition(env, self.sp), "adrift in")

    def test_impossible_boundary_hard(self):
        env = {"volume": {"containment": "impossible", "boundary": "hard"}, "primary_surface": {"normal": "null"}}
        self.assertEqual(derive_preposition(env, self.sp), "within")


class TestOutputFormatter(unittest.TestCase):
    """Verify output_formatter produces correct label structure."""

    def test_render_full_output_contains_labels(self):
        import output_formatter
        data = {
            "subject_phrase": "a confident woman",
            "held_items": [],
            "accessories": [],
            "clothing_items": [],
            "posture_phrase": "",
            "action_clauses": [],
            "env_label": "cafe",
            "env_preposition": "inside",
            "background_elements": [],
            "scene_props": [],
            "lighting_phrase": "bathed in warm amber light",
            "weather_phrase": "",
            "shot_type": "full-body shot",
            "camera_angle": "eye level",
            "camera_framing": "full-body",
            "depth_of_field": "",
            "aesthetic": "cinematic",
            "color_palette": "",
            "render_quality": "high resolution",
            "mood": "warm",
            "pronoun": "She",
        }
        output = output_formatter.render_full_output(data)
        self.assertIn("Subject:", output)
        self.assertIn("Clothing:", output)
        self.assertIn("Action:", output)
        self.assertIn("Environment:", output)
        self.assertIn("Lighting:", output)
        self.assertIn("Camera:", output)
        self.assertIn("Style Details:", output)
        self.assertNotIn("Objects:", output)

    def test_objects_field_appears_when_provided(self):
        import output_formatter
        data = {
            "subject_phrase": "a woman",
            "held_items": [],
            "accessories": [],
            "clothing_items": [],
            "posture_phrase": "",
            "action_clauses": [],
            "env_label": "cafe",
            "env_preposition": "inside",
            "background_elements": [],
            "scene_props": ["a cup of coffee", "a croissant"],
            "lighting_phrase": "",
            "weather_phrase": "",
            "shot_type": "",
            "camera_angle": "",
            "camera_framing": "",
            "depth_of_field": "",
            "aesthetic": "",
            "color_palette": "",
            "render_quality": "",
            "mood": "",
            "pronoun": "She",
        }
        output = output_formatter.render_full_output(data)
        self.assertIn("Objects:", output)

    def test_lead_sentence_no_prefix(self):
        import output_formatter
        data = {
            "subject_phrase": "a woman",
            "held_items": [],
            "accessories": [],
            "clothing_items": [],
            "posture_phrase": "",
            "action_clauses": ["leaning against the counter"],
            "env_label": "cafe",
            "env_preposition": "inside",
            "background_elements": [],
            "scene_props": [],
            "lighting_phrase": "bathed in warm amber light",
            "weather_phrase": "",
            "shot_type": "",
            "camera_angle": "",
            "camera_framing": "",
            "depth_of_field": "",
            "aesthetic": "",
            "color_palette": "",
            "render_quality": "",
            "mood": "",
            "pronoun": "She",
        }
        output = output_formatter.render_full_output(data)
        first_line = output.split("\n")[0]
        # First line should NOT start with a label
        self.assertFalse(first_line.startswith("Subject:"))
        self.assertFalse(first_line.startswith("Clothing:"))


if __name__ == "__main__":
    unittest.main()
