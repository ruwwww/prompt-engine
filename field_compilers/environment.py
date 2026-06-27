"""EnvironmentCompiler — renders the Environment labeled field.

Takes environment fragments (ground, vista, background) and produces
a concise Environment sentence.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import CompilerBase, cap_sentence, natural_join


class EnvironmentCompiler(CompilerBase):
    """Renders the Environment labeled field from environment fragments."""

    def process(
        self,
        env_label: str = "",
        env_preposition: str = "in",
        background_elements: List[str] = None,
        **kwargs,
    ) -> str:
        """Produce the Environment field text.

        Args:
            env_label: The base environment description (e.g. "soft sandy shore").
            env_preposition: Spatial preposition (e.g. "in", "on", "at").
            background_elements: Optional list of background description strings.

        Returns:
            Rendered Environment field, or "" if no data.
        """
        if not env_label:
            return ""

        # Build the base phrase
        # Some env labels like "bright, modern office" already contain articles
        if env_label.startswith("bright, modern office"):
            article = "An" if env_label[0].lower() in "aeiou" else "A"
            parts = [f"{article} {env_label}"]
        else:
            parts = [env_label]

        if background_elements:
            parts.append("with " + natural_join(background_elements))

        return cap_sentence(" ".join(parts))

    def process_from_fragments(
        self,
        fragments: List[Dict[str, Any]],
        env_preposition: str = "in",
        **kwargs,
    ) -> str:
        """Extract environment data from fragments and produce the field."""
        env_label = ""
        background_elements = []

        for f in fragments:
            zone = f.get("zone", "")
            frag_type = f.get("frag_type", "")
            if zone == "environment" and frag_type == "environment":
                text = f.get("text", "")
                if not text.startswith("featuring "):
                    env_label = text
                else:
                    background_elements.append(text)
            elif zone == "environment" and text.startswith("featuring "):
                background_elements.append(f.get("text", ""))

        # Remove 'featuring ' prefix for background elements
        clean_bg = []
        for elem in background_elements:
            if elem.startswith("featuring "):
                elem = elem[len("featuring "):]
            clean_bg.append(elem)

        return self.process(
            env_label=env_label,
            env_preposition=env_preposition,
            background_elements=clean_bg if clean_bg else None,
        )
