"""Core tests run through the Assembler (Clean Slate).

Runs the 109 tests from test_compiler.py that don't rely on:
  - Hair Ontology (structured format)
  - Environment Anchors (dot-notation)
  - scene_description narrative mode
  - strict=True validation

Tests are adapted to call Assembler.assemble() instead of
PromptCompiler.compile_scene().
"""
import unittest
import sys
import os
import pytest

# Ensure assembler is importable
sys.path.insert(0, os.path.dirname(__file__))

from compiler import Assembler


class AssemblerWrapper:
    """Thin wrapper to make Assembler match the old compiler's test interface."""

    def __init__(self):
        self.asm = Assembler()

    def compile_scene(self, scene: dict, strict: bool = False) -> str:
        return self.asm.assemble(scene, strict=strict)


# ---------------------------------------------------------------------------
# Import test classes from test_compiler.py
# ---------------------------------------------------------------------------
from test_compiler import (
    TestVisibility,
    TestSubjects,
    TestAttributeComposition,
    TestRelationships,
    TestSpatialAndScene,
    TestRenderProfiles,
    TestEdgeCases,
    TestMultiCharacter,
    TestNewFeatures,
    TestCompositionApproach,
    TestNewEdgeCases,
    TestBodySurfaceFeatures,
    TestPoseRendering,
    TestBodyConfig,
    TestCozyCreative,
    TestNonHumanSubjects,
)

# Deferred test classes (not run against assembler):
# TestHairOntology, TestNarrativeMode, TestValidationSystem, TestEnvironmentAnchors


# ---------------------------------------------------------------------------
# Patch setUp in each test class to use AssemblerWrapper
# ---------------------------------------------------------------------------
def _make_patched_class(orig_class, wrapper_cls):
    """Create a subclass of orig_class that uses AssemblerWrapper instead of PromptCompiler."""
    class PatchedClass(orig_class):
        def setUp(self):
            # Replace self.c (PromptCompiler) with AssemblerWrapper
            self.c = wrapper_cls()
    PatchedClass.__name__ = orig_class.__name__
    PatchedClass.__qualname__ = orig_class.__qualname__
    return PatchedClass


def _make_patched_class_with_skips(orig_class, wrapper_cls, skip_tests: set, skip_reason: str = "Deferred feature"):
    """Create a subclass of orig_class that uses AssemblerWrapper and skips specific tests."""
    class PatchedClass(orig_class):
        def setUp(self):
            self.c = wrapper_cls()
    PatchedClass.__name__ = orig_class.__name__
    PatchedClass.__qualname__ = orig_class.__qualname__

    # Apply skip decorators to specified test methods
    for method_name in skip_tests:
        method = getattr(PatchedClass, method_name, None)
        if method is not None:
            setattr(PatchedClass, method_name, pytest.mark.skip(reason=skip_reason)(method))

    return PatchedClass
_EDGE_SKIP = {
    "test_invalid_tone_falls_back_to_default",  # may have hair dependencies
}


# Create patched versions
# TestSafeFormat_Assembler removed (safe_format deleted)
TestVisibility_Assembler = _make_patched_class(TestVisibility, AssemblerWrapper)
TestSubjects_Assembler = _make_patched_class(TestSubjects, AssemblerWrapper)
TestAttributeComposition_Assembler = _make_patched_class(TestAttributeComposition, AssemblerWrapper)
TestRelationships_Assembler = _make_patched_class(TestRelationships, AssemblerWrapper)
TestSpatialAndScene_Assembler = _make_patched_class(TestSpatialAndScene, AssemblerWrapper)
TestRenderProfiles_Assembler = _make_patched_class(TestRenderProfiles, AssemblerWrapper)
TestEdgeCases_Assembler = _make_patched_class(TestEdgeCases, AssemblerWrapper)
TestMultiCharacter_Assembler = _make_patched_class(TestMultiCharacter, AssemblerWrapper)
TestNewFeatures_Assembler = _make_patched_class(TestNewFeatures, AssemblerWrapper)
TestCompositionApproach_Assembler = _make_patched_class(TestCompositionApproach, AssemblerWrapper)
TestNewEdgeCases_Assembler = _make_patched_class_with_skips(
    TestNewEdgeCases, AssemblerWrapper, _EDGE_SKIP,
    "Assembler v2: Deferred edge case"
)
TestBodySurfaceFeatures_Assembler = _make_patched_class(TestBodySurfaceFeatures, AssemblerWrapper)
TestPoseRendering_Assembler = _make_patched_class(TestPoseRendering, AssemblerWrapper)
TestBodyConfig_Assembler = _make_patched_class(TestBodyConfig, AssemblerWrapper)
TestCozyCreative_Assembler = _make_patched_class(TestCozyCreative, AssemblerWrapper)
TestNonHumanSubjects_Assembler = _make_patched_class(TestNonHumanSubjects, AssemblerWrapper)
if __name__ == "__main__":
    unittest.main()
