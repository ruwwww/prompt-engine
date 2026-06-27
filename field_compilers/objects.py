"""ObjectsCompiler — renders the Objects labeled output field.

Handles "Inert Prop" inference: any prop not held/used and not a
structural fixture becomes an Object. Includes deduplication, pluralization,
ownership/possession, and spatial context placement.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from field_compilers.base import (
    CompilerBase,
    cap_sentence,
    natural_join,
    a_or_an,
)


def _get_possessive(owner: dict) -> str:
    """Get possessive pronoun for an owner."""
    gender = owner.get("gender", "neutral")
    if gender in ("man", "boy"):
        return "his"
    elif gender in ("woman", "girl"):
        return "her"
    return "their"


def _pluralize_label(label: str, count: int) -> str:
    """Pluralize a label for count > 1."""
    if count == 1:
        return label
    if label.endswith("s"):
        return f"{count} {label}"
    return f"{count} {label}s"


class ObjectsCompiler(CompilerBase):
    """Produces the Objects: field content.

    Collects and deduplicates visible, non-interacted objects/props,
    rendering them with counts, ownership, and spatial context.
    """

    def process(
        self,
        scene_objects: Dict[str, dict] = None,
        relationships: List[dict] = None,
        camera_framing_zones: Set[str] = None,
        **kwargs,
    ) -> str:
        """Render the Objects field.

        Args:
            scene_objects: All scene objects keyed by id.
            relationships: Scene relationships list.
            camera_framing_zones: Visible zones after camera + pose filtering.

        Returns:
            The rendered Objects field text, or empty string.
        """
        if not scene_objects:
            return ""
        if relationships is None:
            relationships = []
        if camera_framing_zones is None:
            camera_framing_zones = set()

        # Track: label -> (count, first_obj)
        label_data: Dict[str, tuple] = {}
        # Track: label -> set of object ids (for exclusion check)
        interacted_ids = set()
        for rel in relationships:
            rel_type = rel.get("type", "")
            if rel_type in ("holding", "using"):
                obj_id = rel.get("object") or rel.get("target")
                if obj_id:
                    interacted_ids.add(obj_id)

        for obj_id, obj in scene_objects.items():
            # Only process inert props
            if obj.get("type") not in ("object", "drink", "item"):
                continue

            # Exclude interacted objects
            if obj_id in interacted_ids:
                continue

            # Visibility check
            obj_zone = obj.get("zone", "LowerBody")
            if obj_zone not in camera_framing_zones:
                continue

            # Get base label
            label = obj.get("label", "")
            if not label:
                template_key = obj.get("template_key", "")
                if template_key:
                    label = template_key.lower().replace("_", " ")
                else:
                    parts = [obj.get("material", ""), obj.get("color", ""), obj.get("type", "object")]
                    label = " ".join(p for p in parts if p).strip()
            if not label:
                continue

            if label not in label_data:
                label_data[label] = (0, obj)
            count, first_obj = label_data[label]
            label_data[label] = (count + 1, first_obj)

        if not label_data:
            return ""

        prop_phrases: List[str] = []
        for label, (count, obj) in label_data.items():
            rendered = _pluralize_label(label, count)

            # Possession
            owner_id = obj.get("owner")
            phrase = ""
            if owner_id and count == 1:
                owner = scene_objects.get(owner_id)
                if owner:
                    possessive = _get_possessive(owner)
                    phrase = f"{possessive} {rendered}"

            # Article
            if not phrase:
                if count > 1:
                    phrase = rendered
                else:
                    if rendered and not rendered.startswith(("a ", "an ", "the ")):
                        article = a_or_an(rendered)
                        phrase = f"{article} {rendered}"
                    else:
                        phrase = rendered

            # Spatial context
            location_id = obj.get("location")
            if location_id:
                location = scene_objects.get(location_id)
                if location:
                    loc_label = location.get("label", location_id)
                    phrase = f"{phrase} on the {loc_label}"

            prop_phrases.append(phrase)

        if not prop_phrases:
            return ""

        return cap_sentence(natural_join(prop_phrases) + " arranged in the scene")
