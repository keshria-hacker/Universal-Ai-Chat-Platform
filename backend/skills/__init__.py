"""
skills — modular skill definitions and execution router. Skills are loaded
from YAML-front-matter SKILL.md files under config/skills/ and executed via
a LiteLLM-backed router.
"""
from skills.registry import SkillRegistry, get_registry
from skills.router import SkillRouter, get_router

__all__ = [
    "SkillRegistry",
    "get_registry",
    "SkillRouter",
    "get_router",
]
