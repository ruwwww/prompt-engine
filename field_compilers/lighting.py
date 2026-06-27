"""LightingCompiler — renders the Lighting labeled field.

Takes lighting/weather phrases and produces a concise Lighting sentence.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import CompilerBase, cap_sentence


class LightingCompiler(CompilerBase):
    """Renders the Lighting labeled field from lighting/weather fragments."""

    def process(
        self,
        lighting_phrase: str = "",
        weather_phrase: str = "",
        **kwargs,
    ) -> str:
        """Produce the Lighting field text.

        Args:
            lighting_phrase: The lighting description (e.g. "golden-hour").
            weather_phrase: Optional weather description (e.g. "breezy").

        Returns:
            Rendered Lighting field, or "" if no data.
        """
        parts = []
        if lighting_phrase:
            parts.append(lighting_phrase.rstrip(".").strip())
        if weather_phrase:
            parts.append(weather_phrase.rstrip(".").strip())
        if not parts:
            return ""
        joined = ". ".join(parts)
        sentences = [s.strip() for s in joined.split(". ")]
        sentences = [s[0].upper() + s[1:] if s else s for s in sentences]
        return ". ".join(sentences) + "."

    def process_from_fragments(
        self,
        fragments: List[Dict[str, Any]],
        **kwargs,
    ) -> str:
        """Extract lighting data from fragments and produce the field."""
        lighting_phrase = ""
        weather_phrase = ""

        for f in fragments:
            zone = f.get("zone", "")
            frag_type = f.get("frag_type", "")
            if zone == "lighting" or frag_type == "lighting":
                text = f.get("text", "")
                if not lighting_phrase:
                    lighting_phrase = text
                else:
                    weather_phrase = text
            elif zone == "weather" or frag_type == "weather":
                weather_phrase = f.get("text", "")

        return self.process(
            lighting_phrase=lighting_phrase,
            weather_phrase=weather_phrase,
        )
