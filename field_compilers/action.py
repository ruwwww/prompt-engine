"""ActionCompiler — renders the Action labeled output field.

Handles pose/posture, relationship chains, overlapping multi-actor
actions, matching held items, and finite-verb conversion for narrative modes.
"""

from __future__ import annotations

from typing import Any, Dict, List

from field_compilers.base import (
    CompilerBase,
    cap_sentence,
    natural_join,
)


def _to_finite(clause_text: str, action_id: str, action_grammar_db: dict, number: str = "singular") -> str:
    """Convert a participial clause to finite form using action_grammar.json."""
    grammar = action_grammar_db.get(action_id)
    if not grammar:
        return clause_text
    participle = grammar.get("participle", "")
    if number == "plural":
        finite = grammar.get("finite_pl", participle)
    else:
        finite = grammar.get("finite_3sg", participle)
    if clause_text.startswith(participle):
        return finite + clause_text[len(participle):]
    elif " " + participle + " " in clause_text:
        return clause_text.replace(" " + participle + " ", " " + finite + " ")
    return clause_text


def _extract_actions(
    frags: List[dict],
    narrative_mode: str = "fact_chain",
    action_grammar_db: dict = None,
    pronoun: str = "She",
) -> tuple:
    """Extract posture phrase and action clauses from actor fragments.

    Returns:
        (posture_phrase, action_clauses)
    """
    posture_phrase = ""
    action_clauses: List[str] = []

    for f in frags:
        zone = f.get("zone", "")
        frag_type = f.get("frag_type", "")
        text = f.get("text", "")

        if frag_type == "relationship":
            clause = f.get("clause_text", text)
            if clause and clause not in action_clauses:
                action_clauses.append(clause)
        elif zone in ("body_config", "_pose", "pose"):
            if text:
                if posture_phrase:
                    posture_texts = [p.strip() for p in posture_phrase.split(",")]
                    if text not in posture_texts:
                        posture_phrase += ", " + text
                else:
                    posture_phrase = text

    # Narrative mode verb chaining
    if narrative_mode == "scene_description" and action_clauses and action_grammar_db:
        rel_info = []
        for f in frags:
            if f.get("frag_type") == "relationship":
                clause = f.get("clause_text", f.get("text", ""))
                rel_info.append((
                    clause,
                    f.get("chain_order", 99),
                    f.get("action_id", ""),
                ))
        rel_info.sort(key=lambda x: x[1])
        if rel_info:
            first_clause, _, first_act_id = rel_info[0]
            number = "plural" if pronoun == "They" else "singular"
            finite_first = _to_finite(first_clause, first_act_id, action_grammar_db, number)
            chained_parts = [finite_first]
            for clause, _, _ in rel_info[1:]:
                chained_parts.append(clause)
            action_clauses = [" ".join(chained_parts)]

    return posture_phrase, action_clauses


def _format_single_action(
    posture_phrase: str,
    action_clauses: List[str],
    pronoun: str,
    narrative_mode: str = "fact_chain",
) -> str:
    """Format a single actor's action field."""
    from output_formatter import format_action_field
    return format_action_field(
        posture_phrase, action_clauses, pronoun,
        is_finite=(narrative_mode == "scene_description"),
    )


def _check_matching_held(
    descriptions: List[dict],
    relationships: List[dict],
    scene_objects: Dict[str, dict],
) -> tuple:
    """Check for matching held items across two actors.

    Returns:
        (matching_clause_or_empty, updated_descriptions)
    """
    if len(descriptions) != 2:
        return "", descriptions

    a1_id, a2_id = descriptions[0]["actor_id"], descriptions[1]["actor_id"]
    a1_held = []
    a2_held = []

    for rel in relationships:
        if rel.get("type") == "holding":
            if rel.get("actor") == a1_id:
                a1_held.append(rel.get("object"))
            elif rel.get("actor") == a2_id:
                a2_held.append(rel.get("object"))

    if len(a1_held) == 1 and len(a2_held) == 1:
        o1 = scene_objects.get(a1_held[0], {})
        o2 = scene_objects.get(a2_held[0], {})
        label1 = o1.get("label", "")
        label2 = o2.get("label", "")
        if label1 and label1 == label2:
            plural = label1 + "s" if not label1.endswith("s") else label1
            clause = f"Both hold their matching {plural}"
            # Remove holding clauses from individual descriptions
            for d in descriptions:
                d["action_clauses"] = [
                    c for c in d["action_clauses"]
                    if not any(c.startswith(p) for p in ("holding ", "holds ", "is holding "))
                ]
            return clause, descriptions

    return "", descriptions


def _build_actor_action_desc(
    actor_id: str,
    posture: str,
    clauses: List[str],
    pronoun: str,
    subject_type: str,
    render_style: str,
) -> dict:
    return {
        "actor_id": actor_id,
        "posture_phrase": posture,
        "action_clauses": list(clauses),
        "pronoun": pronoun,
        "subject_type": subject_type,
        "render_style": render_style,
    }


def _render_style_prefix(render_style: str) -> str:
    if not render_style:
        return ""
    rsl = render_style.lower()
    if "photoreal" in rsl:
        return "realistic "
    if "stylized" in rsl or "anim" in rsl:
        return "animated "
    return render_style + " "


def _format_individual_action(
    desc: dict,
    narrative_mode: str = "fact_chain",
) -> str:
    """Format action for a single actor or non-grouped actor."""
    subj_t = desc["subject_type"]
    prefix = _render_style_prefix(desc.get("render_style", ""))
    identifier = f"The {prefix}{subj_t}"
    parts = []
    verb_be = "" if narrative_mode == "scene_description" else " is"
    if desc["posture_phrase"]:
        parts.append(f"{identifier}{verb_be} {desc['posture_phrase']}")
    for clause in desc["action_clauses"]:
        if parts:
            parts.append(clause)
        else:
            parts.append(f"{identifier}{verb_be} {clause}")
    if parts:
        return cap_sentence(", ".join(parts))
    return ""


class ActionCompiler(CompilerBase):
    """Produces the Action: field content.

    Handles pose/posture, relationship action chains, multi-actor
    same-action collapsing, matching held items, and narrative mode
    verb chaining.
    """

    def process(
        self,
        fragments_by_actor: Dict[str, List[dict]] = None,
        relationships: List[dict] = None,
        scene_objects: Dict[str, dict] = None,
        groups: List[dict] = None,
        narrative_mode: str = "fact_chain",
        action_grammar_db: dict = None,
        **kwargs,
    ) -> str:
        """Render the Action field.

        Args:
            fragments_by_actor: Mapping of actor_id -> list of fragment dicts.
            relationships: Scene relationships list.
            scene_objects: All scene objects keyed by id.
            groups: Scene groups.
            narrative_mode: "fact_chain" or "scene_description".
            action_grammar_db: Loaded action_grammar.json for finite verb conversion.

        Returns:
            The rendered Action field text, or empty string.
        """
        if not fragments_by_actor:
            return ""
        if relationships is None:
            relationships = []
        if scene_objects is None:
            scene_objects = {}
        if groups is None:
            groups = []

        # Extract actions per actor
        actor_actions: Dict[str, tuple] = {}
        for actor_id, frags in fragments_by_actor.items():
            obj = scene_objects.get(actor_id, {})
            gender = obj.get("gender", "person")
            subj_type = "person"
            # Get subject type from fragments
            for f in frags:
                if f.get("zone") == "_subject_type":
                    subj_type = f.get("text", "person")
                    break
            if subj_type == "person":
                subj_type = gender if gender in ("woman", "man") else "person"
            pronoun = "She"
            if subj_type in ("man", "boy"):
                pronoun = "He"
            elif subj_type not in ("woman", "girl"):
                pronoun = "They"

            posture, clauses = _extract_actions(
                frags, narrative_mode, action_grammar_db, pronoun
            )
            actor_actions[actor_id] = _build_actor_action_desc(
                actor_id, posture, clauses, pronoun, subj_type,
                obj.get("render_style", ""),
            )

        # --- Single actor ---
        if len(actor_actions) == 1:
            desc = list(actor_actions.values())[0]
            if desc["posture_phrase"] or desc["action_clauses"]:
                return _format_single_action(
                    desc["posture_phrase"], desc["action_clauses"],
                    desc["pronoun"], narrative_mode,
                )
            return ""

        # --- Multi-actor ---
        # Build group membership
        actor_to_group: Dict[str, dict] = {}
        for g in groups:
            for member in g.get("members", []):
                if member in actor_actions:
                    actor_to_group[member] = g

        grouped_actors: Dict[str, List[dict]] = {}
        non_grouped: List[dict] = []
        for actor_id, desc in actor_actions.items():
            g = actor_to_group.get(actor_id)
            if g:
                grouped_actors.setdefault(g["id"], []).append(desc)
            else:
                non_grouped.append(desc)

        # Check matching held items for all descriptions
        all_descs = list(actor_actions.values())
        matching_clause, all_descs = _check_matching_held(
            all_descs, relationships, scene_objects
        )

        # Update grouped/non-grouped with potentially modified descriptions
        # (after matching held items may have removed holding clauses)
        desc_by_id = {d["actor_id"]: d for d in all_descs}
        for gid in grouped_actors:
            grouped_actors[gid] = [desc_by_id.get(m["actor_id"], m) for m in grouped_actors[gid]]
        non_grouped = [desc_by_id.get(m["actor_id"], m) for m in non_grouped]

        action_parts: List[str] = []

        # Check if all same action
        action_sets = []
        for d in all_descs:
            action_sets.append(
                d["posture_phrase"] + " | " + " & ".join(d["action_clauses"])
            )
        all_same = len(set(action_sets)) == 1
        all_have_content = any(
            d["posture_phrase"] or d["action_clauses"] for d in all_descs
        )

        if all_same and all_have_content and len(all_descs) > 1:
            pronoun = "Both" if len(all_descs) == 2 else "They"
            act = _format_single_action(
                all_descs[0]["posture_phrase"],
                all_descs[0]["action_clauses"],
                pronoun, narrative_mode,
            )
            action_parts.append(act)
        elif matching_clause:
            action_parts.append(cap_sentence(matching_clause))
            # Render individual actions for non-held clauses
            for d in all_descs:
                individual = _format_individual_action(d, narrative_mode)
                if individual:
                    action_parts.append(individual)
        else:
            # Render grouped actors
            for gid, members in grouped_actors.items():
                mem_sets = [
                    m["posture_phrase"] + " | " + " & ".join(m["action_clauses"])
                    for m in members
                ]
                if len(set(mem_sets)) == 1:
                    pronoun = "Both" if len(members) == 2 else "They"
                    act = _format_single_action(
                        members[0]["posture_phrase"],
                        members[0]["action_clauses"],
                        pronoun, narrative_mode,
                    )
                    action_parts.append(act)
                else:
                    for m in members:
                        individual = _format_individual_action(m, narrative_mode)
                        if individual:
                            action_parts.append(individual)

            # Render non-grouped actors
            for d in non_grouped:
                act = _format_single_action(
                    d["posture_phrase"], d["action_clauses"],
                    d["pronoun"], narrative_mode,
                )
                if act:
                    action_parts.append(act)

        return " ".join(action_parts)
