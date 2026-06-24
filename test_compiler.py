import unittest
from compiler import PromptCompiler

class TestPromptCompiler(unittest.TestCase):
    def setUp(self):
        self.compiler = PromptCompiler()

    def test_visibility_evaluation_close_up(self):
        scene = {
            "camera": {
                "framing": "close_up"
            },
            "objects": {
                "human_1": {
                    "type": "human",
                    "gender": "woman",
                    "Face": {
                        "expression": "smiling"
                    },
                    "Hair": {
                        "color": "brown",
                        "length": "long"
                    },
                    "Feet": {
                        "owned_item_id": "shoes_1"
                    }
                },
                "shoes_1": {
                    "type": "clothing",
                    "template_key": "Shoes",
                    "color": "black"
                }
            }
        }
        compiled = self.compiler.compile_scene(scene)
        self.assertIn("smiling", compiled)
        self.assertIn("long", compiled)
        self.assertNotIn("shoes", compiled)
        self.assertNotIn("black", compiled)

    def test_attribute_composition_clean_spacing(self):
        template = "{fit} {color} {material} hoodie"
        ctx_all = {"fit": "oversized", "color": "black", "material": "cotton"}
        self.assertEqual(
            self.compiler.safe_format(template, ctx_all),
            "oversized black cotton hoodie"
        )
        
        ctx_partial = {"color": "red"}
        self.assertEqual(
            self.compiler.safe_format(template, ctx_partial),
            "red hoodie"
        )

    def test_persona_resolution_and_pose_visibility(self):
        scene = {
            "camera": {
                "framing": "medium"
            },
            "pose": "hands_behind_back",
            "objects": {
                "human_1": {
                    "type": "human",
                    "persona": "urban_influencer",
                    "Face": {
                        "expression": "grinning"
                    }
                },
                "hoodie_1": {
                    "type": "clothing",
                    "template_key": "Hoodie",
                    "fit": "oversized",
                    "color": "black",
                    "material": "cotton"
                },
                "ring_1": {
                    "type": "accessory",
                    "template_key": "Ring",
                    "material": "silver"
                }
            }
        }
        compiled = self.compiler.compile_scene(scene)
        self.assertIn("grinning woman", compiled)
        self.assertNotIn("smiling woman", compiled)
        self.assertIn("long wavy brown hair", compiled)
        self.assertNotIn("ring", compiled)

    def test_relationship_rendering_and_variants(self):
        scene = {
            "camera": {
                "framing": "medium"
            },
            "pose": "standing",
            "render_profile": "character_sheet",
            "objects": {
                "human_1": {
                    "type": "human",
                    "persona": "urban_influencer"
                },
                "coffee_cup_1": {
                    "type": "drink",
                    "template_key": "CoffeeCup",
                    "material": "ceramic",
                    "color": "white"
                }
            },
            "relationships": [
                {
                    "type": "holding",
                    "actor": "human_1",
                    "object": "coffee_cup_1"
                }
            ]
        }
        compiled = self.compiler.compile_scene(scene)
        self.assertIn("woman holding a cup of ceramic coffee cup", compiled)

    def test_relationship_visibility_occlusion(self):
        scene = {
            "camera": {
                "framing": "medium"
            },
            "pose": "hands_behind_back",
            "render_profile": "character_sheet",
            "objects": {
                "human_1": {
                    "type": "human",
                    "persona": "urban_influencer"
                },
                "coffee_cup_1": {
                    "type": "drink",
                    "template_key": "CoffeeCup",
                    "material": "ceramic",
                    "color": "white"
                }
            },
            "relationships": [
                {
                    "type": "holding",
                    "actor": "human_1",
                    "object": "coffee_cup_1"
                }
            ]
        }
        compiled = self.compiler.compile_scene(scene)
        self.assertNotIn("holding", compiled)

    def test_spatial_relationship_and_placements(self):
        scene = {
            "camera": {
                "framing": "full_body"
            },
            "pose": "standing",
            "render_profile": "cinematic",
            "environment": {
                "type": "alley",
                "lighting": "neon",
                "weather": "rainy"
            },
            "composition": {
                "type": "cinematic"
            },
            "anchors": {
                "primary": "human_1"
            },
            "placements": {
                "car_1": "background"
            },
            "objects": {
                "human_1": {
                    "type": "human",
                    "persona": "urban_influencer"
                },
                "car_1": {
                    "type": "vehicle",
                    "template_key": "Car",
                    "color": "red"
                }
            },
            "relationships": [
                {
                    "type": "standing_next_to",
                    "subject": "human_1",
                    "target": "car_1"
                }
            ]
        }
        compiled = self.compiler.compile_scene(scene)
        self.assertIn("rain-soaked neon-lit alley", compiled)
        self.assertIn("woman standing next to red car in background", compiled)
        self.assertIn("cinematic still photography", compiled)

if __name__ == "__main__":
    unittest.main()
