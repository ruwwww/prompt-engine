import os
import json
import re

class PromptCompiler:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.templates = self.load_json("templates.json", {})
        self.personas = self.load_json("personas.json", {})
        self.poses = self.load_json("poses.json", {})
        self.metadata = self.load_json("attribute_metadata.json", {})
        self.profiles = self.load_json("render_profiles.json", {})
        self.actions = self.load_json("actions.json", {})
        
        # Stage 5 databases
        self.spatial = self.load_json("spatial_relationships.json", {})
        self.environments = self.load_json("environments.json", {})
        self.lighting = self.load_json("lighting.json", {})
        self.weather = self.load_json("weather.json", {})
        self.composition = self.load_json("composition.json", {})
        
        self.camera_zones = {
            "close_up": ["Face", "Hair"],
            "medium": ["Face", "Hair", "UpperBody", "Hands"],
            "full_body": ["Face", "Hair", "UpperBody", "Hands", "LowerBody", "Feet"]
        }

    def load_json(self, filename, default):
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def safe_format(self, template_str, context):
        placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", template_str)
        kwargs = {}
        for p in placeholders:
            val = context.get(p, "")
            kwargs[p] = str(val) if val is not None else ""
        rendered = template_str.format(**kwargs)
        return re.sub(r'\s+', ' ', rendered).strip()

    def get_noun_phrase(self, obj_id, scene, resolved_human=None):
        obj = scene.get("objects", {}).get(obj_id)
        if not obj:
            return obj_id

        phrase = ""
        if obj.get("type") == "human":
            phrase = resolved_human.get("gender") if resolved_human else obj.get("gender", "person")
        else:
            template_key = obj.get("template_key")
            template = self.templates.get(template_key)
            if template:
                phrase = self.safe_format(template, obj)
            else:
                color = obj.get("color", "")
                material = obj.get("material", "")
                t = obj.get("type", "item")
                phrase = f"{material} {color} {t}".replace("  ", " ").strip()

        # Apply placements details if any (e.g. "red car in background")
        placement = scene.get("placements", {}).get(obj_id)
        if placement:
            phrase = f"{phrase} in {placement}"

        return phrase

    def compile_scene(self, scene):
        # 1. Resolve Persona defaults
        human_id = None
        human_obj = None
        for obj_id, obj in scene.get("objects", {}).items():
            if obj.get("type") == "human":
                human_id = obj_id
                human_obj = obj
                break

        resolved_human = {}
        if human_obj:
            persona_name = human_obj.get("persona")
            if persona_name and persona_name in self.personas:
                resolved_human = json.loads(json.dumps(self.personas[persona_name]))

            for k, v in human_obj.items():
                if isinstance(v, dict) and k in resolved_human and isinstance(resolved_human[k], dict):
                    resolved_human[k].update(v)
                else:
                    resolved_human[k] = v

        # 2. Determine Visible Zones
        framing = scene.get("camera", {}).get("framing", "full_body")
        visible_zones = list(self.camera_zones.get(framing, self.camera_zones["full_body"]))

        pose_name = scene.get("pose")
        if pose_name and pose_name in self.poses:
            hidden_zones = self.poses[pose_name].get("hidden_zones", [])
            for hz in hidden_zones:
                if hz in visible_zones:
                    visible_zones.remove(hz)

        # Anchors and Placements priority adjustment helper
        def get_priority(base_priority, related_obj_ids):
            pri = base_priority
            anchors = scene.get("anchors", {})
            placements = scene.get("placements", {})
            for r_id in related_obj_ids:
                if anchors.get("primary") == r_id:
                    pri += 15
                elif anchors.get("secondary") == r_id:
                    pri += 5
                
                # Placement modifications
                if placements.get(r_id) == "background":
                    pri -= 10
            return pri

        # 3. Collect Candidate Fragments
        candidates = []

        if human_obj:
            for zone in visible_zones:
                zone_data = resolved_human.get(zone)
                if not zone_data:
                    continue

                owned_item_id = zone_data.get("owned_item_id")
                if owned_item_id:
                    owned_item = scene.get("objects", {}).get(owned_item_id)
                    if owned_item:
                        meta = self.metadata.get(owned_item.get("type"), {"tags": [], "priority": 50})
                        template_key = owned_item.get("template_key")
                        template = self.templates.get(template_key)
                        if template:
                            candidates.append({
                                "zone": zone,
                                "type": "owned_item",
                                "tags": meta.get("tags", []),
                                "priority": get_priority(meta.get("priority", 50), [human_id, owned_item_id]),
                                "text": self.safe_format(template, owned_item)
                            })
                else:
                    meta_key = "expression" if zone == "Face" else "hair" if zone == "Hair" else zone.lower()
                    meta = self.metadata.get(meta_key, {"tags": [], "priority": 50})
                    template = self.templates.get(zone)
                    if template:
                        ctx = {**zone_data, "gender": resolved_human.get("gender", "person")}
                        text = self.safe_format(template, ctx)
                        if text:
                            candidates.append({
                                "zone": zone,
                                "type": "native",
                                "tags": meta.get("tags", []),
                                "priority": get_priority(meta.get("priority", 50), [human_id]),
                                "text": text
                            })

        # 4. Process Standard & Spatial Relationships
        # Combine actions list with spatial relationships list
        all_relationships = scene.get("relationships", [])
        for rel in all_relationships:
            rel_type = rel.get("type")
            
            # Check actions first, then spatial relationships
            rel_def = self.actions.get(rel_type)
            is_spatial = False
            if not rel_def:
                rel_def = self.spatial.get(rel_type)
                is_spatial = True
                
            if not rel_def:
                continue

            # Validate role constraints
            valid_roles = True
            related_ids = []
            for role_name, constraint in rel_def.get("roles", {}).items():
                target_id = rel.get(role_name)
                target_obj = scene.get("objects", {}).get(target_id)
                if not target_obj:
                    valid_roles = False
                    break
                related_ids.append(target_id)
                allowed_types = constraint.get("allowed", [])
                if target_obj.get("type") not in allowed_types:
                    valid_roles = False
                    break

            if not valid_roles:
                continue

            # Check required visibility zones
            visible = True
            for role_name, req_zone in rel_def.get("required_zones", {}).items():
                participant_id = rel.get(role_name)
                participant_obj = scene.get("objects", {}).get(participant_id)
                if participant_obj and participant_obj.get("type") == "human":
                    if req_zone not in visible_zones:
                        visible = False
                        break
            if not visible:
                continue

            # Resolve templates & variants
            template = rel_def.get("template", "")
            for variant in rel_def.get("variants", []):
                when = variant.get("when", {})
                match = True
                for when_key, when_val in when.items():
                    if when_key.endswith("_type"):
                        role_name = when_key[:-5]
                        target_id = rel.get(role_name)
                        target_obj = scene.get("objects", {}).get(target_id)
                        if not target_obj or target_obj.get("type") != when_val:
                            match = False
                            break
                if match:
                    template = variant.get("template", template)
                    break

            role_phrases = {}
            for role_name in rel_def.get("roles", {}).keys():
                target_id = rel.get(role_name)
                role_phrases[role_name] = self.get_noun_phrase(target_id, scene, resolved_human)

            rendered_relationship = template.format(**role_phrases)

            candidates.append({
                "zone": "relationship",
                "type": "relationship",
                "tags": rel_def.get("tags", ["spatial" if is_spatial else "action"]),
                "priority": get_priority(rel_def.get("priority", 50), related_ids),
                "text": rendered_relationship
            })

        # 5. Process Environment, Lighting, Weather, and Composition
        env_config = scene.get("environment", {})
        env_type = env_config.get("type")
        
        # Environment
        if env_type and env_type in self.environments:
            env_def = self.environments[env_type]
            
            # Resolve Lighting template/default
            lighting_val = env_config.get("lighting", env_def.get("default_lighting"))
            lighting_str = ""
            if lighting_val in self.lighting:
                lighting_str = self.lighting[lighting_val].get("template", lighting_val)
            else:
                lighting_str = lighting_val
                
            # Resolve Weather template/default
            weather_val = env_config.get("weather", env_def.get("default_weather"))
            weather_str = ""
            if weather_val in self.weather:
                weather_str = self.weather[weather_val].get("template", weather_val)
            else:
                weather_str = weather_val
                
            # Render Environment template
            env_template = env_def.get("template", "{weather} {lighting} {type}")
            env_text = env_template.format(weather=weather_str, lighting=lighting_str, type=env_type)
            env_text = re.sub(r'\s+', ' ', env_text).strip()
            
            candidates.append({
                "zone": "environment",
                "type": "environment",
                "tags": ["environment"],
                "priority": 65,
                "text": env_text
            })
            
            # Add separate lighting candidate
            if lighting_str:
                candidates.append({
                    "zone": "lighting",
                    "type": "lighting",
                    "tags": ["lighting"],
                    "priority": 55,
                    "text": lighting_str
                })
                
            # Add separate weather candidate
            if weather_str:
                candidates.append({
                    "zone": "weather",
                    "type": "weather",
                    "tags": ["weather"],
                    "priority": 50,
                    "text": weather_str
                })

        # Composition
        comp_config = scene.get("composition", {})
        comp_type = comp_config.get("type")
        if comp_type and comp_type in self.composition:
            comp_text = self.composition[comp_type].get("template", comp_type)
            candidates.append({
                "zone": "composition",
                "type": "composition",
                "tags": ["composition"],
                "priority": 88,
                "text": comp_text
            })

        # 6. Apply Render Profile Filtering & Budget
        profile_name = scene.get("render_profile", "character_sheet")
        profile = self.profiles.get(profile_name, self.profiles.get("character_sheet", {}))
        
        include_tags = set(profile.get("include_tags", []))
        max_fragments = profile.get("max_fragments", 99)

        # Filter by tags
        filtered = [c for c in candidates if any(t in include_tags for t in c["tags"])]

        # Sort by priority
        filtered.sort(key=lambda x: x["priority"], reverse=True)

        # Apply fragment budget
        budgeted = filtered[:max_fragments]

        # 7. Render & Compose
        rendered_parts = {}
        other_texts = [] # holds spatial relationships, environment details, lighting, weather, composition
        
        for c in budgeted:
            if c["type"] in ["relationship", "environment", "lighting", "weather", "composition"]:
                other_texts.append(c["text"])
            else:
                rendered_parts[c["zone"]] = c["text"]

        prompt_segments = []
        face_str = rendered_parts.get("Face")
        hair_str = rendered_parts.get("Hair")
        
        if face_str and hair_str:
            base_prompt = f"{face_str} with {hair_str}"
        elif face_str:
            base_prompt = face_str
        elif hair_str:
            gender = resolved_human.get("gender", "person")
            base_prompt = f"{gender} with {hair_str}"
        else:
            base_prompt = resolved_human.get("gender", "person") if human_obj else ""

        if base_prompt:
            prompt_segments.append(base_prompt)

        # Append relations, weather, lighting, composition, environment details
        for ot in other_texts:
            prompt_segments.append(ot)

        # Append clothing/accessory
        order = ["UpperBody", "LowerBody", "Feet"]
        for zone in order:
            if zone in rendered_parts:
                prompt_segments.append(rendered_parts[zone])

        return ", ".join([ps for ps in prompt_segments if ps])
