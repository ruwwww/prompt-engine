import unittest
from compiler import PromptCompiler

class TestPromptCompiler(unittest.TestCase):
    def setUp(self):
        self.compiler = PromptCompiler()

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
        
        # 1. Test environment formatting: "rain-soaked neon-lit alley"
        self.assertIn("rain-soaked neon-lit alley", compiled)
        
        # 2. Test spatial relationship rendering with background placement details:
        # "woman standing next to red car in background"
        self.assertIn("woman standing next to red car in background", compiled)
        
        # 3. Test cinematic composition style
        self.assertIn("cinematic still photography", compiled)

if __name__ == "__main__":
    unittest.main()
