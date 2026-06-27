"""StyleCompiler — renders the Style Details labeled field.

Takes aesthetic, color palette, render quality, and mood
and produces a concise Style Details description.
"""

from __future__ import annotations

from .base import CompilerBase, cap_sentence


class StyleCompiler(CompilerBase):
    """Renders the Style Details labeled field from style parameters."""

    def process(
        self,
        aesthetic: str = "",
        color_palette: str = "",
        render_quality: str = "",
        mood: str = "",
        **kwargs,
    ) -> str:
        """Produce the Style Details field text.

        Args:
            aesthetic: The aesthetic/style name (e.g. "photorealistic", "cinematic").
            color_palette: Color palette description (e.g. "vibrant reds").
            render_quality: Render quality description (e.g. "high detail").
            mood: Mood description (e.g. "dreamy", "melancholic").

        Returns:
            Rendered Style Details field, or "" if no data.
        """
        parts = []
        if aesthetic:
            parts.append(aesthetic)
        if color_palette:
            parts.append(f"with {color_palette}")
        if render_quality:
            parts.append(render_quality)
        if mood:
            parts.append(f"conveying a {mood} mood")
        return cap_sentence(", ".join(parts))
