"""
schemas/scene.py — Pydantic models for scene.json input validation.

These models strictly map to the valid scene.json structure consumed by
the PromptCompiler pipeline.  Validation errors produce clear HTTP 422
responses stating exactly which field is missing or invalid.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class Camera(BaseModel):
    framing: str = Field(default="full_body", description="Camera framing: full_body, medium, close_up")
    shot_type: Optional[str] = None
    angle: Optional[str] = None
    depth_of_field: Optional[str] = None


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Environment(BaseModel):
    type: str = Field(..., description="Environment type key (e.g. cafe, alley, beach)")
    lighting: Optional[str] = None
    weather: Optional[str] = None
    geolocation: Optional[str] = None
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# Body Config
# ---------------------------------------------------------------------------

class HeadConfig(BaseModel):
    tilt: Optional[str] = None
    turn: Optional[str] = None


class GazeConfig(BaseModel):
    direction: Optional[str] = None
    target: Optional[str] = None


class ArmsConfig(BaseModel):
    left: Optional[str] = None
    right: Optional[str] = None


class LegsConfig(BaseModel):
    position: Optional[str] = None


class TorsoConfig(BaseModel):
    lean: Optional[str] = None
    position: Optional[str] = None


class BodyConfig(BaseModel):
    head: Optional[HeadConfig] = None
    gaze: Optional[GazeConfig] = None
    arms: Optional[ArmsConfig] = None
    legs: Optional[LegsConfig] = None
    torso: Optional[TorsoConfig] = None


# ---------------------------------------------------------------------------
# Scene Object (actor, clothing, fixture, etc.)
# ---------------------------------------------------------------------------

class SceneObject(BaseModel):
    type: str = Field(default="human", description="Object type: human, creature, clothing, fixture, environment, etc.")
    id: Optional[str] = None
    subject: Optional[str] = None
    gender: Optional[str] = None
    attire: Optional[str] = None
    template_key: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    fit: Optional[str] = None
    pattern: Optional[str] = None
    species: Optional[str] = None
    face: Optional[Dict[str, Any]] = Field(default=None, alias="Face")
    hair: Optional[Dict[str, Any]] = Field(default=None, alias="Hair")
    eyes: Optional[Dict[str, Any]] = Field(default=None, alias="Eyes")
    ears: Optional[Dict[str, Any]] = Field(default=None, alias="Ears")
    tusks: Optional[Dict[str, Any]] = Field(default=None, alias="Tusks")
    jaw: Optional[Dict[str, Any]] = Field(default=None, alias="Jaw")
    morphology: Optional[Dict[str, Any]] = None
    upper_body: Optional[Dict[str, Any]] = Field(default=None, alias="UpperBody")
    lower_body: Optional[Dict[str, Any]] = Field(default=None, alias="LowerBody")
    feet: Optional[Dict[str, Any]] = Field(default=None, alias="Feet")
    hands: Optional[Dict[str, Any]] = Field(default=None, alias="Hands")
    headwear: Optional[Dict[str, Any]] = Field(default=None, alias="Headwear")
    body_surface_features: Optional[List[Dict[str, Any]]] = None
    body_config: Optional[BodyConfig] = None
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Additional zone data")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------

class Relationship(BaseModel):
    type: str = Field(..., description="Relationship type (e.g. holding, sitting, leaning_on)")
    actor: Optional[str] = None
    subject: Optional[str] = None
    subject1: Optional[str] = None
    object: Optional[str] = None
    target: Optional[str] = None
    container: Optional[str] = None
    subject2: Optional[str] = None
    chain_order: Optional[int] = None


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

class Composition(BaseModel):
    type: str = Field(..., description="Composition type (e.g. cinematic, rule_of_thirds)")


# ---------------------------------------------------------------------------
# Top-level scene input
# ---------------------------------------------------------------------------

class SceneInput(BaseModel):
    camera: Optional[Camera] = None
    environment: Optional[Environment] = None
    pose: Optional[str] = None
    render_profile: Optional[str] = Field(default="character_sheet", description="Render profile name")
    style: Optional[str] = None
    composition: Optional[Composition] = None
    tone: Optional[str] = None
    mood: Optional[str] = None
    output_format: Optional[str] = Field(default="legacy", description="Output format: legacy or labeled")
    anchors: Optional[Dict[str, str]] = None
    placements: Optional[Dict[str, str]] = None
    body_config: Optional[Dict[str, Dict[str, Any]]] = None
    objects: Dict[str, Any] = Field(default_factory=dict, description="Scene objects keyed by ID")
    relationships: Optional[List[Relationship]] = None

    model_config = {"extra": "allow"}
