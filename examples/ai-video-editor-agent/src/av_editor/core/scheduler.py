"""Deterministic stage scheduler (§1.3).

Defines the canonical node order of the state graph and provides a resumable,
idempotent executor: each stage declares its dependencies; already-completed
stages (recorded in the DB) are skipped on resume; conditional routing is
handled by the orchestrator through :meth:`Scheduler.next_stage` overrides.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from av_editor.logging import get_logger

log = get_logger("av_editor.scheduler")


class Stage(str, Enum):
    INTAKE = "intake"
    MEDIA_CONFORM = "media_conform"
    PROXY_GENERATION = "proxy_generation"
    VISION_ANALYSIS = "vision_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    TRANSCRIPT_ANALYSIS = "transcript_analysis"
    BENCHMARK_STYLE_ANALYSIS = "benchmark_style_analysis"
    EDITORIAL_PLAN = "editorial_plan"
    ROUGH_CUT_CONSTRUCTION = "rough_cut_construction"
    BROLL_SELECTION = "broll_selection"
    SUBTITLE_GENERATION = "subtitle_generation"
    SOUND_DESIGN = "sound_design"
    COLOR_PREPARATION = "color_preparation"
    TIMELINE_ASSEMBLY = "timeline_assembly"
    QC_RENDER = "qc_render"
    CRITIC_REVIEW = "critic_review"
    PATCH_APPLICATION = "patch_application"
    FINAL_EXPORT = "final_export"
    ARCHIVE_REPORT = "archive_report"
    # Conditional error routes (§1.3)
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    COMPLIANCE_FAILURE = "compliance_failure"
    VISION_UNAVAILABLE_ERROR = "vision_unavailable_error"


LINEAR_ORDER: list[Stage] = [
    Stage.INTAKE,
    Stage.MEDIA_CONFORM,
    Stage.PROXY_GENERATION,
    Stage.VISION_ANALYSIS,
    Stage.AUDIO_ANALYSIS,
    Stage.TRANSCRIPT_ANALYSIS,
    Stage.BENCHMARK_STYLE_ANALYSIS,
    Stage.EDITORIAL_PLAN,
    Stage.ROUGH_CUT_CONSTRUCTION,
    Stage.BROLL_SELECTION,
    Stage.SUBTITLE_GENERATION,
    Stage.SOUND_DESIGN,
    Stage.COLOR_PREPARATION,
    Stage.TIMELINE_ASSEMBLY,
    Stage.QC_RENDER,
    Stage.CRITIC_REVIEW,
    Stage.FINAL_EXPORT,
    Stage.ARCHIVE_REPORT,
]

DEPENDENCIES: dict[Stage, list[Stage]] = {
    Stage.MEDIA_CONFORM: [Stage.INTAKE],
    Stage.PROXY_GENERATION: [Stage.MEDIA_CONFORM],
    Stage.VISION_ANALYSIS: [Stage.PROXY_GENERATION],
    Stage.AUDIO_ANALYSIS: [Stage.MEDIA_CONFORM],
    Stage.TRANSCRIPT_ANALYSIS: [Stage.AUDIO_ANALYSIS],
    Stage.BENCHMARK_STYLE_ANALYSIS: [Stage.INTAKE],
    Stage.EDITORIAL_PLAN: [Stage.VISION_ANALYSIS, Stage.TRANSCRIPT_ANALYSIS],
    Stage.ROUGH_CUT_CONSTRUCTION: [Stage.EDITORIAL_PLAN],
    Stage.BROLL_SELECTION: [Stage.ROUGH_CUT_CONSTRUCTION],
    Stage.SUBTITLE_GENERATION: [Stage.ROUGH_CUT_CONSTRUCTION],
    Stage.SOUND_DESIGN: [Stage.ROUGH_CUT_CONSTRUCTION],
    Stage.COLOR_PREPARATION: [Stage.ROUGH_CUT_CONSTRUCTION],
    Stage.TIMELINE_ASSEMBLY: [Stage.BROLL_SELECTION, Stage.SUBTITLE_GENERATION,
                              Stage.SOUND_DESIGN, Stage.COLOR_PREPARATION],
    Stage.QC_RENDER: [Stage.TIMELINE_ASSEMBLY],
    Stage.CRITIC_REVIEW: [Stage.QC_RENDER],
    Stage.FINAL_EXPORT: [Stage.CRITIC_REVIEW],
    Stage.ARCHIVE_REPORT: [Stage.FINAL_EXPORT],
}


@dataclass
class StageSpec:
    stage: Stage
    fn: Callable[[dict[str, Any]], dict[str, Any]]
    optional: bool = False  # skippable when prerequisites unavailable (e.g. benchmark off)


@dataclass
class Scheduler:
    """Executes stages in dependency order with completion bookkeeping."""

    specs: dict[Stage, StageSpec] = field(default_factory=dict)
    completed: set[Stage] = field(default_factory=set)
    skipped: set[Stage] = field(default_factory=set)

    def register(self, spec: StageSpec) -> None:
        self.specs[spec.stage] = spec

    def ready(self, stage: Stage) -> bool:
        deps = DEPENDENCIES.get(stage, [])
        return all(d in self.completed or d in self.skipped for d in deps)

    def next_stage(self, route_override: Stage | None = None) -> Stage | None:
        if route_override is not None:
            return route_override
        for stage in LINEAR_ORDER:
            if stage in self.completed or stage in self.skipped:
                continue
            if self.ready(stage):
                return stage
        return None

    def run_stage(self, stage: Stage, state: dict[str, Any]) -> dict[str, Any]:
        spec = self.specs[stage]
        log.info("stage_start", stage=stage.value)
        new_state = spec.fn(state)
        self.completed.add(stage)
        log.info("stage_done", stage=stage.value)
        return new_state

    def skip(self, stage: Stage, reason: str) -> None:
        log.info("stage_skipped", stage=stage.value, reason=reason)
        self.skipped.add(stage)

    def mark_completed(self, stage: Stage) -> None:
        """Used on resume when the DB says a stage already finished."""
        self.completed.add(stage)
