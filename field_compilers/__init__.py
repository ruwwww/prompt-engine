"""Field compilers package — 8 specialized modules for the labeled output fields.

Each compiler handles exactly one field (Subject, Clothing, Action, Objects,
Environment, Lighting, Camera, Style) and follows the CompilerBase interface.
"""

from field_compilers.subject import SubjectCompiler
from field_compilers.clothing import ClothingCompiler
from field_compilers.action import ActionCompiler
from field_compilers.objects import ObjectsCompiler
from field_compilers.environment import EnvironmentCompiler
from field_compilers.lighting import LightingCompiler
from field_compilers.camera import CameraCompiler
from field_compilers.style import StyleCompiler

__all__ = [
    "SubjectCompiler",
    "ClothingCompiler",
    "ActionCompiler",
    "ObjectsCompiler",
    "EnvironmentCompiler",
    "LightingCompiler",
    "CameraCompiler",
    "StyleCompiler",
]
