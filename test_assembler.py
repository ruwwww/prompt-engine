"""Tests for the Clean Slate Assembler."""
import unittest
from compiler import (
    Assembler, deep_merge,
    resolve_blueprint, apply_delta, resolve_references,
    filter_by_camera, render_to_text, apply_relationships,
    apply_environment, apply_style_tone, CAMERA_FRAMING_MAP,
)
from compiler_legacy import safe_format


class TestSafeFormat(unittest.TestCase):
    def test_simple_string(self):
        self.assertEqual(safe_format("hello {name}", {"name": "world"}), "hello world")

    def test_missing_key(self):
        self.assertEqual(safe_format("hello {name}", {}), "hello")

    def test_slot_descriptor(self):
        tpl = {"head": "hair", "slots": {"color": {"position": "pre"}, "length": {"position": "pre"}}}
        ctx = {"color": "brown", "length": "long"}
        result = safe_format(tpl, ctx)
        self.assertIn("long", result)
        self.assertIn("brown", result)
        self.assertIn("hair", result)

    def test_article_adjustment(self):
        self.assertEqual(safe_format("a {item}", {"item": "apple"}), "an apple")
        self.assertEqual(safe_format("an {item}", {"item": "banana"}), "a banana")


class TestDeepMerge(unittest.TestCase):
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_nested_merge(self):
        base = {"Face": {"expression": "smiling"}}
        override = {"Face": {"color": "green"}}
        result = deep_merge(base, override)
        self.assertEqual(result["Face"]["expression"], "smiling")
        self.assertEqual(result["Face"]["color"], "green")

    def test_override_wins(self):
        base = {"Face": {"expression": "smiling"}}
        override = {"Face": {"expression": "laughing"}}
        result = deep_merge(base, override)
        self.assertEqual(result["Face"]["expression"], "laughing")


class TestResolveBlueprint(unittest.TestCase):
    def setUp(self):
        from compiler import _load_json
        self.subjects_db = _load_json("subjects.json")
        self.attires_db = _load_json("attires.json")

    def test_orc_warrior_basic(self):
        obj = {
            "type": "creature",
            "subject": "orc_warrior",
            "Face": {"expression": "snarling"},
            "Tusks": {"size": "large", "material": "ivory"},
        }
        result = resolve_blueprint(obj, self.subjects_db, self.attires_db, {})
        self.assertIn("Tusks", result)
        self.assertEqual(result["Face"]["expression"], "snarling")

    def test_subject_defaults_applied(self):
        obj = {"type": "human", "subject": "urban_influencer"}
        result = resolve_blueprint(obj, self.subjects_db, self.attires_db, {})
        self.assertIn("Face", result)
        self.assertIn("Hair", result)

    def test_scene_overrides_wins(self):
        obj = {"type": "human", "subject": "urban_influencer", "Face": {"expression": "laughing"}}
        result = resolve_blueprint(obj, self.subjects_db, self.attires_db, {})
        self.assertEqual(result["Face"]["expression"], "laughing")


class TestApplyDelta(unittest.TestCase):
    def test_simple_override(self):
        components = {"Face": {"expression": "smiling"}}
        overrides = {"Face.expression": "laughing"}
        result = apply_delta(components, overrides)
        self.assertEqual(result["Face"]["expression"], "laughing")

    def test_no_mutation(self):
        components = {"Face": {"expression": "smiling"}}
        overrides = {"Face.expression": "laughing"}
        apply_delta(components, overrides)
        self.assertEqual(components["Face"]["expression"], "smiling")

    def test_new_component(self):
        components = {}
        overrides = {"Tusks.size": "large"}
        result = apply_delta(components, overrides)
        self.assertEqual(result["Tusks"]["size"], "large")


class TestFilterByCamera(unittest.TestCase):
    def setUp(self):
        from compiler import _load_json
        self.poses_db = _load_json("poses.json")

    def test_close_up_excludes_lower(self):
        components = {"Face": {}, "UpperBody": {}, "LowerBody": {}}
        result = filter_by_camera(components, "close_up")
        self.assertIn("Face", result)
        self.assertNotIn("LowerBody", result)

    def test_full_body_includes_all(self):
        components = {"Face": {}, "UpperBody": {}, "LowerBody": {}, "Feet": {}}
        result = filter_by_camera(components, "full_body")
        self.assertEqual(len(result), 4)

    def test_pose_hides_zones(self):
        components = {"Face": {}, "UpperBody": {}, "Feet": {}}
        result = filter_by_camera(components, "full_body", "sitting", self.poses_db)
        self.assertNotIn("Feet", result)


@unittest.skip("Legacy TestRenderToText skipped in V2")
class TestRenderToText(unittest.TestCase):
    def setUp(self):
        from compiler import _load_json
        self.templates_db = _load_json("templates.json")
        self.metadata_db = _load_json("attribute_metadata.json")
        self.profiles_db = _load_json("render_profiles.json")

    def test_face_renders(self):
        visible = {"Face": {"expression": "smiling"}, "Hair": {"color": "brown", "length": "long", "style": "wavy"}}
        result = render_to_text(visible, "character_sheet", self.templates_db, self.metadata_db, self.profiles_db)
        texts = [f["text"] for f in result]
        self.assertTrue(any("smiling" in t for t in texts))

    def test_tusks_render(self):
        visible = {"Tusks": {"size": "large", "material": "ivory"}}
        result = render_to_text(visible, "character_sheet", self.templates_db, self.metadata_db, self.profiles_db)
        texts = [f["text"] for f in result]
        self.assertTrue(any("tusks" in t for t in texts))


class TestAssemblerIntegration(unittest.TestCase):
    def setUp(self):
        self.assembler = Assembler()

    def test_empty_scene(self):
        result = self.assembler.assemble({"camera": {"framing": "full_body"}, "objects": {}})
        self.assertEqual(result, "")

    def test_orc_basic(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {
                "orc1": {
                    "type": "creature",
                    "subject": "orc_warrior",
                    "Face": {"expression": "snarling"},
                    "Tusks": {"size": "large", "material": "ivory"},
                }
            }
        }
        result = self.assembler.assemble(scene)
        self.assertIn("snarling", result)
        self.assertIn("tusks", result.lower())

    def test_elf_basic(self):
        scene = {
            "camera": {"framing": "medium"},
            "objects": {
                "elf1": {
                    "type": "creature",
                    "subject": "elf_archer",
                    "Face": {"expression": "focused"},
                    "Ears": {"shape": "pointed", "length": "long"},
                }
            }
        }
        result = self.assembler.assemble(scene)
        self.assertIn("focused", result)
        self.assertIn("pointed", result.lower())

    def test_human_basic(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {
                "h1": {
                    "type": "human",
                    "Face": {"expression": "smiling"},
                    "Hair": {"color": "brown", "length": "long", "style": "wavy"},
                }
            }
        }
        result = self.assembler.assemble(scene)
        self.assertIn("smiling", result)


class TestCameraFraming(unittest.TestCase):
    def setUp(self):
        self.assembler = Assembler()

    def test_camera_framing_close_up_injected(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertIn("shot of", result.lower())

    def test_camera_framing_medium_injected(self):
        scene = {
            "camera": {"framing": "medium"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertIn("shot of", result.lower())

    def test_camera_framing_full_body_injected(self):
        scene = {
            "camera": {"framing": "full_body"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertIn("full-body shot of", result.lower())

    def test_camera_framing_default_injected(self):
        scene = {
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertIn("full-body shot of", result.lower())

    def test_camera_framing_disabled(self):
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene, inject_camera_descriptor=False)
        self.assertNotIn("shot of", result)

    def test_camera_framing_user_override_wins(self):
        scene = {
            "camera": {"framing": "close_up"},
            "Camera": {"custom": "custom camera text"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertNotIn("shot of", result)

    def test_camera_framing_still_filters_lower_body(self):
        """Camera framing gates visibility even when descriptor is ON."""
        scene = {
            "camera": {"framing": "close_up"},
            "objects": {"orc1": {"type": "creature", "subject": "orc_warrior", "Face": {"expression": "snarling"}, "Tusks": {"size": "large"}}}
        }
        result = self.assembler.assemble(scene)
        self.assertIn("shot of", result.lower())
        self.assertNotIn("boots", result.lower())


if __name__ == "__main__":
    unittest.main()
