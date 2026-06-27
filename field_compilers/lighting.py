"""LightingCompiler — renders the Lighting labeled output field.

Formats the atmospheric lighting and weather description from
the environment's envelope data.
"""

from __future__ import annotations

from typing import Any

from field_compilers.base import CompilerBase


class LightingCompiler(CompilerBase):
    """Produces the Lighting: field content."""

    def process(
        self,
        lighting_phrase: str = "",
        weather_phrase: str = "",
        **kwargs,
    ) -> str:
        """Render the Lighting field.

        Args:
            lighting_phrase: The resolved lighting description.
            weather_phrase: The resolved weather description (optional).

        Returns:
            The rendered Lighting field text, or empty string.
        """
        # Phase 0 stub — delegates to existing logic in Assembler.
        return ""
