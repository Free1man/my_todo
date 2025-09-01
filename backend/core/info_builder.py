from __future__ import annotations
from typing import Any, Dict, Callable, Optional
from pydantic import BaseModel
from backend.core.templates import build_template, model_schema

# type aliases
ActionSpecs = Dict[str, type[BaseModel]]
ModelSpecs  = Dict[str, type[BaseModel]]
ExamplesFn  = Callable[[Any], Dict[str, dict]]  # state -> {action_name: payload}

def build_ruleset_info(
    *,
    ruleset_name: str,
    state: Any,
    action_specs: ActionSpecs,
    model_specs: Optional[ModelSpecs] = None,
    examples_fn: Optional[ExamplesFn] = None,
    defaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    actions = {
        name: {
            "schema":   model_schema(model),
            "template": build_template(model),
            "example":  None,  # filled below if examples_fn provided
        }
        for name, model in action_specs.items()
    }
    if examples_fn:
        examples = examples_fn(state) or {}
        for k, ex in examples.items():
            if k in actions:
                actions[k]["example"] = ex

    models = {}
    for k, mdl in (model_specs or {}).items():
        models[k] = {"schema": model_schema(mdl), "template": build_template(mdl)}

    return {
        "ruleset": ruleset_name,
        "map": getattr(state, "map", None).model_dump() if getattr(state, "map", None) else None,
        "defaults": defaults or {},
        "actions": actions,
        "models": models,
        "notes": "Templates are built from model defaults; fill IDs/coords as needed.",
    }

# Optional: mixin to avoid per-ruleset boilerplate
class InfoMixin:
    ACTION_SPECS: ActionSpecs = {}
    MODEL_SPECS:  ModelSpecs  = {}
    def build_examples(self, state) -> Dict[str, dict]:  # override if you want concrete examples
        return {}
    def default_info(self, state) -> Dict[str, Any]:
        return build_ruleset_info(
            ruleset_name=getattr(self, "name", "unknown"),
            state=state,
            action_specs=self.ACTION_SPECS,
            model_specs=self.MODEL_SPECS,
            examples_fn=self.build_examples,
            defaults={},
        )
    # Provide a public .info(state) method
    def info(self, state) -> Dict[str, Any]:
        return self.default_info(state)
