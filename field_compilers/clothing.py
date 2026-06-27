"""ClothingCompiler — renders the Clothing labeled output field.

Handles detection of matching items across actors (collapsing into
shared descriptions like "Both wear matching X"), layer ordering
with "over" preposition, and individual actor attribution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from field_compilers.base import (
    CompilerBase,
    cap_sentence,
    natural_join,
    join_with_over,
    pronoun_verb,
)

# Zones collected as clothing items (sorted by layer_order descending)
CLOTHING_ZONES = {"UpperBody", "LowerBody", "Feet"}

# Zones collected as accessories (rendered after clothing items, e.g. "with gold bracelets")
ACCESSORY_ZONES = {"Hands", "Jewelry", "Accessories", "Headwear"}


def _extract_clothing(
    frags: List[dict],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extract clothing items and accessories from an actor's fragments.

    Returns:
        (clothing_items, accessories)
        clothing_items is a list of {"layer_order": int, "label": str}
        sorted by layer_order descending (outermost first).
        accessories is a list of label strings.
    """
    clothing_items: List[Dict[str, Any]] = []
    accessories: List[str] = []

    for f in frags:
        zone = f.get("zone", "")
        text = f.get("text", "")

        if zone in CLOTHING_ZONES:
            label = text.strip()
            if label and not any(
                item["label"] == label for item in clothing_items
            ):
                clothing_items.append(
                    {"layer_order": f.get("priority", 50), "label": label}
                )
        elif zone in ACCESSORY_ZONES:
            label = text.strip()
            if label and label not in accessories:
                accessories.append(label)

    # Sort by layer_order descending (outermost first)
    clothing_items.sort(key=lambda x: x.get("layer_order", 0), reverse=True)
    return clothing_items, accessories


def _render_style_prefix(render_style: str) -> str:
    """Convert a render_style value to a prefix string for clothing identifiers.

    "photoreal" → "realistic "
    "stylized", "animated" → "animated "
    other → f"{render_style} "
    empty → ""
    """
    if not render_style:
        return ""
    rsl = render_style.lower()
    if "photoreal" in rsl:
        return "realistic "
    if "stylized" in rsl or "anim" in rsl:
        return "animated "
    return render_style + " "


def _format_individual_clothing(
    clothing_items: List[Dict[str, Any]],
    pronoun: str,
    accessories: List[str] = None,
) -> str:
    """Format a single actor's clothing items and accessories.

    Example: "She wears a black hoodie over a white t-shirt."
    With accessories: "She wears a black hoodie over a white t-shirt, with gold bracelets."
    """
    if accessories is None:
        accessories = []
    labels = [item["label"] for item in clothing_items]
    if not labels and not accessories:
        return ""
    subj, _, verb = pronoun_verb(pronoun)
    parts = []
    if labels:
        joined = join_with_over(labels)
        parts.append(f"{subj} {verb} {joined}")
    if accessories:
        acc_joined = natural_join(accessories)
        if parts:
            parts.append(f"with {acc_joined}")
        else:
            parts.append(f"{subj} {verb} {acc_joined}")
    return " ".join(parts) + "."


def _format_group_clothing(
    members: List[dict],
    group_label: str,
) -> str:
    """Format clothing for a group of actors.

    If all members wear identical clothing → "Both/They wear matching X over Y."
    If different → "The woman wears X. The man wears Y."
    """
    # Collect clothing label sets per member (including accessories)
    member_label_sets: List[Tuple[str, ...]] = []
    member_acc_sets: List[Tuple[str, ...]] = []
    member_clothing = []
    member_accessories = []
    for m in members:
        labels = tuple(
            sorted([item["label"] for item in m["clothing_items"]])
        )
        accs = tuple(sorted(m.get("accessories", [])))
        member_label_sets.append(labels)
        member_acc_sets.append(accs)
        member_clothing.append(m["clothing_items"])
        member_accessories.append(m.get("accessories", []))

    all_identical = (
        len(set(member_label_sets)) == 1
        and len(set(member_acc_sets)) == 1
        and len(member_clothing[0]) > 0
    )

    if all_identical:
        pronoun = "Both" if len(members) == 2 else "They"
        sorted_items = sorted(
            member_clothing[0],
            key=lambda x: x.get("layer_order", 0),
            reverse=True,
        )
        labels = [item["label"] for item in sorted_items]
        if labels:
            labels[0] = "matching " + labels[0]
            joined = join_with_over(labels)
            base = f"{pronoun} wear {joined}"
            # Add accessories if present
            if member_accessories[0]:
                base += f", with {natural_join(member_accessories[0])}"
            return base + "."

    # Different clothing — render each member individually
    parts = []
    for m in members:
        subj_t = m.get("subject_type", "person")
        prefix = _render_style_prefix(m.get("render_style", ""))
        identifier = f"The {prefix}{subj_t}"

        sorted_items = sorted(
            m["clothing_items"],
            key=lambda x: x.get("layer_order", 0),
            reverse=True,
        )
        labels = [item["label"] for item in sorted_items]
        accs = m.get("accessories", [])
        if labels:
            joined = join_with_over(labels)
            base = f"{identifier} wears {joined}"
            if accs:
                base += f", with {natural_join(accs)}"
            parts.append(base + ".")
        elif accs:
            parts.append(f"{identifier} wears {natural_join(accs)}.")

    return " ".join(parts)


class ClothingCompiler(CompilerBase):
    """Produces the Clothing: field content.

    Detects matching clothing sets across actors in the same group,
    applies "over" layering for multi-layer outfits, and formats
    individual actor descriptions when clothing differs.
    """

    def process(
        self,
        fragments_by_actor: Dict[str, List[dict]] = None,
        groups: List[dict] = None,
        scene_objects: Dict[str, dict] = None,
        **kwargs,
    ) -> str:
        """Render the Clothing field.

        Args:
            fragments_by_actor: Mapping of actor_id -> list of fragment dicts.
            groups: Scene groups (e.g. [{"id": "couple_1", "members": [...], "label": "..."}]).
            scene_objects: All scene objects keyed by id.

        Returns:
            The rendered Clothing field text, or empty string.
        """
        if not fragments_by_actor:
            return ""
        if groups is None:
            groups = []
        if scene_objects is None:
            scene_objects = {}

        # Extract clothing items per actor
        actor_clothing: Dict[str, List[Dict[str, Any]]] = {}
        actor_accessories: Dict[str, List[str]] = {}
        for actor_id, frags in fragments_by_actor.items():
            items, accs = _extract_clothing(frags)
            actor_clothing[actor_id] = items
            actor_accessories[actor_id] = accs

        # Build a description dict per actor for group rendering
        actor_descs: Dict[str, dict] = {}
        for actor_id in fragments_by_actor:
            obj = scene_objects.get(actor_id, {})
            gender = obj.get("gender", "person")
            morphology = obj.get("morphology", {})
            subj_type = "person"
            # Try to get subject type from fragments
            for f in fragments_by_actor[actor_id]:
                if f.get("zone") == "_subject_type":
                    subj_type = f.get("text", "person")
                    break
            if subj_type == "person":
                subj_type = gender if gender in ("woman", "man") else "person"

            actor_descs[actor_id] = {
                "clothing_items": actor_clothing.get(actor_id, []),
                "accessories": actor_accessories.get(actor_id, []),
                "subject_type": subj_type,
                "pronoun": "She" if subj_type in ("woman", "girl") else "He" if subj_type in ("man", "boy") else "They",
                "render_style": obj.get("render_style", ""),
            }

        # Map actors to groups
        actor_to_group: Dict[str, dict] = {}
        for g in groups:
            for member in g.get("members", []):
                if member in actor_descs:
                    actor_to_group[member] = g

        # --- Single actor ---
        if len(actor_descs) == 1:
            actor_id = list(actor_descs.keys())[0]
            desc = actor_descs[actor_id]
            return _format_individual_clothing(
                desc["clothing_items"], desc["pronoun"],
                accessories=actor_accessories.get(actor_id, []),
            )

        # --- Multi-actor ---
        grouped_actors: Dict[str, List[dict]] = {}
        non_grouped_actors: List[dict] = []
        for actor_id, desc in actor_descs.items():
            g = actor_to_group.get(actor_id)
            if g:
                grouped_actors.setdefault(g["id"], []).append(desc)
            else:
                non_grouped_actors.append(desc)

        clothing_parts: List[str] = []

        # Render grouped actors
        for gid, members in grouped_actors.items():
            group_label = next(
                (g.get("label", "") for g in groups if g.get("id") == gid),
                "",
            )
            part = _format_group_clothing(members, group_label)
            if part:
                clothing_parts.append(part)

        # Render non-grouped actors individually
        for desc in non_grouped_actors:
            part = _format_individual_clothing(
                desc["clothing_items"], desc["pronoun"],
                accessories=desc.get("accessories", []),
            )
            if part:
                clothing_parts.append(part)

        return " ".join(clothing_parts)
