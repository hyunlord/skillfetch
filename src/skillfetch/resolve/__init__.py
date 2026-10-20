"""Conflict and redundancy resolution over pre-extracted constraints.

Runtime half: must never import a model client (see tests/test_decoupling.py).
"""

from skillfetch.resolve.models import Constraint, Finding, Resolution, Skill
from skillfetch.resolve.relation import Relation, complementary, skill_relation
from skillfetch.resolve.report import render_finding
from skillfetch.resolve.resolver import resolve_set

__all__ = [
    "Constraint",
    "Finding",
    "Relation",
    "Resolution",
    "Skill",
    "complementary",
    "render_finding",
    "resolve_set",
    "skill_relation",
]
