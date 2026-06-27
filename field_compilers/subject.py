"""SubjectCompiler — renders the Subject labeled output field.

The Subject field must always identify distinct actors individually,
even when groups exist. A group label is just the wrapper for the
summary sentence; the Subject field itself contains structural
identification of the individuals.
"""

from __future__ import annotations

from typing import Any, Dict, List

from field_compilers.base import (
    CompilerBase,
    cap_sentence,
    natural_join,
    a_or_an,
)


def _get_subject_type(gender: str, morphology: dict) -> str:
    """Get the subject type string (e.g., 'orc', 'elf', 'woman', 'man')."""
    if morphology and morphology.get("type"):
        return morphology["type"]
    if gender in ("woman", "man", "person"):
        return gender
    if gender:
        return gender
    return "person"


# Zones and tags related to identity
IDENTITY_FACE_ZONES = {"Face"}
IDENTITY_HAIR_ZONES = {"Hair"}
IDENTITY_EXTRA_ZONES = {"Tusks", "Ears", "Jaw", "Eyes"}
IDENTITY_SUBJECT_ZONE = "_subject_type"


def _build_individual_identity(
    actor_id: str,
    frags: List[dict],
    scene_objects: Dict[str, dict],
) -> str:
    """Build an individual identity description for a single actor from its fragments.

    Produces phrases like:
        "a smiling woman with long wavy brown hair and green eyes"
        "a snarling orc with large ivory tusks"
        "a focused elf with pointed ears and silver braided hair"
    """
    obj = scene_objects.get(actor_id, {})
    gender = obj.get("gender", "person")
    morphology = obj.get("morphology", {})
    subject_type = _get_subject_type(gender, morphology)

    identity_adjectives: List[str] = []
    hair_phrase = ""
    extra_identity_texts: List[str] = []

    for f in frags:
        zone = f.get("zone", "")
        text = f.get("text", "")

        if zone == IDENTITY_SUBJECT_ZONE:
            subject_type = text
        elif zone in IDENTITY_HAIR_ZONES:
            hair_phrase = text
        elif zone in IDENTITY_FACE_ZONES:
            if text and text not in identity_adjectives:
                identity_adjectives.append(text)
        elif zone in IDENTITY_EXTRA_ZONES:
            if text and text not in extra_identity_texts:
                extra_identity_texts.append(text)

    render_style = obj.get("render_style", "")

    # Build: [render_style] [face] [subject_type]
    parts: List[str] = []
    if render_style:
        parts.append(render_style)
    if identity_adjectives:
        parts.append(", ".join(identity_adjectives))
    parts.append(subject_type)
    identity_phrase = " ".join(parts)

    # Build: with [hair] and [extra_features]
    with_parts: List[str] = []
    if hair_phrase:
        with_parts.append(hair_phrase)
    for extra in extra_identity_texts:
        with_parts.append(extra)

    if with_parts:
        identity_phrase += " with " + natural_join(with_parts)

    # Add indefinite article if not starting with one
    if identity_phrase and not identity_phrase.lower().startswith(
        ("a ", "an ", "the ", "his ", "her ", "their ")
    ):
        article = a_or_an(identity_phrase)
        identity_phrase = f"{article} {identity_phrase}"

    return identity_phrase


class SubjectCompiler(CompilerBase):
    """Produces the Subject: field content.

    Always renders individual actor identities, even when groups exist.
    For a group, the group label is used as a wrapper phrase, but the
    individual identities are still enumerated.
    """

    def process(
        self,
        fragments_by_actor: Dict[str, List[dict]] = None,
        groups: List[dict] = None,
        scene_objects: Dict[str, dict] = None,
        **kwargs,
    ) -> str:
        """Render the Subject field.

        Args:
            fragments_by_actor: Mapping of actor_id -> list of fragment dicts.
            groups: Scene groups (e.g. [{"id": "couple_1", "members": [...], "label": "stylish couple"}]).
            scene_objects: All scene objects keyed by id.

        Returns:
            The rendered Subject field text, or empty string.
        """
        if not fragments_by_actor:
            return ""
        if groups is None:
            groups = []
        if scene_objects is None:
            scene_objects = {}

        # Build individual identity phrases per actor
        individual_descs: Dict[str, str] = {}
        for actor_id, frags in fragments_by_actor.items():
            desc = _build_individual_identity(actor_id, frags, scene_objects)
            individual_descs[actor_id] = desc

        # Categorize actors by group membership
        actor_to_group: Dict[str, dict] = {}
        for g in groups:
            for member in g.get("members", []):
                if member in individual_descs:
                    actor_to_group[member] = g

        # --- Single actor: just return the description ---
        if len(individual_descs) == 1:
            return cap_sentence(list(individual_descs.values())[0])

        # --- Multi-actor with groups ---
        # If all actors belong to the same group, produce:
        #   "A stylish couple: a man with dark curly hair and a woman with blonde hair"
        if groups and len(actor_to_group) == len(individual_descs):
            # All actors are in groups
            group_phrases: List[str] = []
            processed_groups: set = set()

            for actor_id in individual_descs:
                g = actor_to_group.get(actor_id)
                if g and g["id"] not in processed_groups:
                    processed_groups.add(g["id"])
                    label = g.get("label") or g.get("type") or "group"
                    # Collect all members' descriptions for this group
                    member_descs = []
                    for m_id in g.get("members", []):
                        if m_id in individual_descs:
                            member_descs.append(individual_descs[m_id])

                    if member_descs:
                        # "a stylish couple: a man with dark curly hair and a woman with blonde hair"
                        article = a_or_an(label)
                        inner = natural_join(member_descs)
                        group_phrases.append(f"{article} {label}: {inner}")
                    else:
                        article = a_or_an(label)
                        group_phrases.append(f"{article} {label}")
                elif g is None:
                    # Actor not in any group
                    group_phrases.append(individual_descs[actor_id])

            if group_phrases:
                return cap_sentence(natural_join(group_phrases))

        # --- Multi-actor without groups, or mixed group/non-group ---
        # Produce structural list: "a woman with brown hair, a man with short black hair, and a woman with red hair"
        all_descs = list(individual_descs.values())
        return cap_sentence(natural_join(all_descs))
