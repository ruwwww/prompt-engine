"""CameraCompiler — renders the Camera labeled field.

Takes shot type, angle, framing, depth of field, and focus
and produces a concise Camera description.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import CompilerBase, cap_sentence


class CameraCompiler(CompilerBase):
    """Renders the Camera labeled field from camera parameters."""

    def process(
        self,
        shot_type: str = "",
        angle: str = "",
        framing: str = "",
        depth_of_field: str = "",
        focus: str = "",
        **kwargs,
    ) -> str:
        """Produce the Camera field text.

        Args:
            shot_type: Type of shot (e.g. "close-up", "medium", "wide").
            angle: Camera angle (e.g. "low angle", "eye-level").
            framing: Framing description (e.g. "full-body", "medium").
            depth_of_field: Depth of field description (e.g. "shallow depth of field").
            focus: What the camera focuses on (e.g. "the subject's eyes").

        Returns:
            Rendered Camera field, or "" if no data.
        """
        parts = []
        if shot_type:
            parts.append(shot_type)
        elif framing:
            parts.append(f"{framing} shot")
        if angle:
            parts.append(f"from {angle}")
        if framing and shot_type:
            parts.append(framing)
        sentence = " ".join(parts)
        if depth_of_field:
            sentence += f", {depth_of_field}"
        if focus:
            sentence += f", focusing on the {focus}"
        return cap_sentence(sentence)
