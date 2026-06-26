"""
output_formatter.py

Renders assembled scene data into the eight-field labeled output format.
The compiler produces structured scene data. This module renders it.
Depends on: no external libraries beyond standard Python.
"""


def format_lead_sentence(subject_phrase: str, action_clause: str,
                          env_clause: str, atmosphere_detail: str) -> str:
    parts = [subject_phrase]
    if action_clause:
        parts.append(action_clause)
    if env_clause:
        parts.append(env_clause)
    if atmosphere_detail:
        parts.append(atmosphere_detail)
    sentence = " ".join(parts).strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    return sentence


def format_subject_field(identity_phrase: str, held_items: list[str],
                          accessories: list[str]) -> str:
    parts = [identity_phrase]
    if accessories:
        parts.append("wearing " + _join_list(accessories))
    if held_items:
        parts.append("holding " + _join_list(held_items))
    return _cap_sentence(" ".join(parts))


def format_clothing_field(clothing_items: list[dict]) -> str:
    sorted_items = sorted(clothing_items, key=lambda x: x.get("layer_order", 0), reverse=True)
    labels = [item["label"] for item in sorted_items]
    if not labels:
        return ""
    return "She wears " + _join_list_with_over(labels) + "."


def format_action_field(posture_phrase: str, action_clauses: list[str]) -> str:
    parts = []
    if posture_phrase:
        parts.append(f"She is {posture_phrase}")
    for clause in action_clauses:
        if parts:
            parts.append(clause)
        else:
            parts.append(f"She is {clause}")
    return _cap_sentence(", ".join(parts))


def format_environment_field(env_label: str, env_preposition: str,
                              background_elements: list[str]) -> str:
    parts = [f"A {env_label}"]
    if background_elements:
        parts.append("with " + _join_list(background_elements))
    return _cap_sentence(" ".join(parts))


def format_objects_field(scene_props: list[str]) -> str | None:
    if not scene_props:
        return None
    return _cap_sentence(_join_list(scene_props) + " arranged in the scene") + "."


def format_lighting_field(lighting_phrase: str, weather_phrase: str) -> str:
    parts = []
    if lighting_phrase:
        parts.append(lighting_phrase)
    if weather_phrase:
        parts.append(weather_phrase)
    return _cap_sentence(". ".join(parts))


def format_camera_field(shot_type: str, angle: str, framing: str,
                         depth_of_field: str) -> str:
    parts = []
    if shot_type:
        parts.append(shot_type)
    if angle:
        parts.append(f"from {angle}")
    if framing:
        parts.append(framing)
    sentence = " ".join(parts)
    if depth_of_field:
        sentence += f", {depth_of_field}"
    return _cap_sentence(sentence)


def format_style_field(aesthetic: str, color_palette: str,
                        render_quality: str, mood: str) -> str:
    parts = []
    if aesthetic:
        parts.append(aesthetic)
    if color_palette:
        parts.append(f"with {color_palette}")
    if render_quality:
        parts.append(render_quality)
    if mood:
        parts.append(f"conveying a {mood} mood")
    return _cap_sentence(", ".join(parts))


def render_full_output(scene_data: dict) -> str:
    lead = format_lead_sentence(
        scene_data.get("subject_phrase", ""),
        scene_data.get("action_clauses", [""])[0] if scene_data.get("action_clauses") else "",
        f"{scene_data.get('env_preposition', 'in')} a {scene_data.get('env_label', '')}",
        scene_data.get("lighting_phrase", "")
    )
    subject = format_subject_field(
        scene_data.get("subject_phrase", ""),
        scene_data.get("held_items", []),
        scene_data.get("accessories", [])
    )
    clothing = format_clothing_field(scene_data.get("clothing_items", []))
    action = format_action_field(
        scene_data.get("posture_phrase", ""),
        scene_data.get("action_clauses", [])
    )
    environment = format_environment_field(
        scene_data.get("env_label", ""),
        scene_data.get("env_preposition", "in"),
        scene_data.get("background_elements", [])
    )
    objects = format_objects_field(scene_data.get("scene_props", []))
    lighting = format_lighting_field(
        scene_data.get("lighting_phrase", ""),
        scene_data.get("weather_phrase", "")
    )
    camera = format_camera_field(
        scene_data.get("shot_type", ""),
        scene_data.get("camera_angle", ""),
        scene_data.get("camera_framing", ""),
        scene_data.get("depth_of_field", "")
    )
    style = format_style_field(
        scene_data.get("aesthetic", ""),
        scene_data.get("color_palette", ""),
        scene_data.get("render_quality", ""),
        scene_data.get("mood", "")
    )

    lines = [lead, ""]
    lines.append(f"Subject: {subject}")
    lines.append(f"Clothing: {clothing}")
    lines.append(f"Action: {action}")
    lines.append(f"Environment: {environment}")
    if objects:
        lines.append(f"Objects: {objects}")
    lines.append(f"Lighting: {lighting}")
    lines.append(f"Camera: {camera}")
    lines.append(f"Style Details: {style}")

    return "\n".join(lines)


# ── Private helpers ──────────────────────────────────────────────────────────

def _join_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _join_list_with_over(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} over {items[1]}"
    return f"{items[0]} over " + _join_list(items[1:])


def _cap_sentence(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
    if text and not text.endswith("."):
        text += "."
    return text
