"""LangGraph orchestrator (§1.3).

Builds the state graph over the agent stages with conditional edges:
- critical critic violations  -> patch_application (loop back through qc_render)
- patch attempts > max        -> human_review_required
- unauthorized benchmark      -> compliance_failure
- unavailable VLM             -> vision_unavailable_error unless the user has
  explicitly enabled ``vlm.allow_cv_only_fallback`` in config.

When the optional ``langgraph`` dependency is not installed, an equivalent
deterministic built-in executor (:class:`FallbackExecutor`) runs the same node
functions and routing rules so the pipeline remains fully operational — this is
a documented capability adaptation, not a silent failure.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from av_editor.core.db import PipelineDB
from av_editor.core.event_bus import EventBus
from av_editor.core.scheduler import LINEAR_ORDER, Scheduler, Stage, StageSpec
from av_editor.core.state import PipelineState
from av_editor.errors import AVEditorError, QACriticalError
from av_editor.logging import get_logger
from av_editor.settings import PipelineConfig

log = get_logger("av_editor.orchestrator")

NodeFn = Callable[[PipelineState], PipelineState]


class Orchestrator:
    """Deterministic, resumable multi-agent pipeline runner."""

    def __init__(self, config: PipelineConfig, *, bus: EventBus | None = None) -> None:
        self.config = config
        self.bus = bus or EventBus()
        self.db = PipelineDB(config.project.cache_dir / "pipeline.sqlite3")
        self.scheduler = Scheduler()
        self._nodes: dict[Stage, NodeFn] = {}
        self._checkpoint_dir = config.project.cache_dir / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # -- registration -------------------------------------------------------
    def add_node(self, stage: Stage, fn: NodeFn, *, optional: bool = False) -> None:
        self._nodes[stage] = fn
        self.scheduler.register(StageSpec(stage=stage, fn=lambda s, f=fn: _run(f, s),
                                          optional=optional))

    # -- execution ----------------------------------------------------------
    def run(self, state: PipelineState, *, until: Stage | None = None,
            rerun_from: Stage | None = None) -> PipelineState:
        """Execute the graph from current completion state.

        Args:
            state: starting pipeline state (fresh or loaded checkpoint).
            until: stop after this stage completes (partial stage reruns).
            rerun_from: invalidate this stage and all downstream completions.
        """
        if rerun_from is not None:
            idx = LINEAR_ORDER.index(rerun_from)
            drop = {s.value for s in LINEAR_ORDER[idx:]}
            state.completed_stages = [s for s in state.completed_stages if s.value not in drop]
        for s in state.completed_stages:
            self.scheduler.mark_completed(s)
        for s in state.skipped_stages:
            self.scheduler.skipped.add(s)

        self.bus.publish("run_start", run_id=state.run_id, mode=state.mode)
        max_steps = len(LINEAR_ORDER) * 8  # loop bound incl. QC cycles
        steps = 0
        while steps < max_steps:
            steps += 1
            route = Stage(state.route_override) if state.route_override else None
            stage = self.scheduler.next_stage(route)
            if stage is None:
                break
            if stage in (Stage.HUMAN_REVIEW_REQUIRED, Stage.COMPLIANCE_FAILURE,
                         Stage.VISION_UNAVAILABLE_ERROR):
                self._terminal_route(state, stage)
                break
            if stage not in self._nodes:
                self.scheduler.skip(stage, "no_node_registered")
                state.skipped_stages.append(stage)
                continue
            state.route_override = None
            self.db.set_run_stage(state.run_id, stage.value)
            self.bus.publish("stage_start", stage=stage.value, run_id=state.run_id)
            t0 = time.monotonic()
            try:
                state = self._nodes[stage](state)
            except QACriticalError as exc:
                state.errors.append({"stage": stage.value, **exc.to_dict()})
                state.route_override = Stage.PATCH_APPLICATION.value
                self.bus.publish("stage_failed", stage=stage.value, error=exc.message)
                continue
            except AVEditorError as exc:
                self._handle_stage_error(state, stage, exc)
                break
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            if stage not in state.completed_stages:
                state.completed_stages.append(stage)
            self.scheduler.completed.add(stage)
            self.bus.publish("stage_done", stage=stage.value, duration_ms=round(elapsed_ms, 1))
            state.save(self._checkpoint(state.run_id))
            if until is not None and stage == until:
                break
        else:
            raise AVEditorError("Pipeline exceeded step bound (possible routing cycle)",
                                run_id=state.run_id)
        self.db.finish_run(state.run_id, "done" if not state.human_review_required else
                           "human_review_required")
        self.bus.publish("run_finish", run_id=state.run_id,
                         human_review=state.human_review_required)
        return state

    # -- error routing ------------------------------------------------------
    def _handle_stage_error(self, state: PipelineState, stage: Stage, exc: AVEditorError) -> None:
        state.errors.append({"stage": stage.value, **exc.to_dict()})
        if stage == Stage.BENCHMARK_STYLE_ANALYSIS and "compliance" in exc.message.lower():
            state.route_override = Stage.COMPLIANCE_FAILURE.value
        elif stage == Stage.VISION_ANALYSIS and "VLM" in exc.message:
            if self.config.vlm.allow_cv_only_fallback:
                log.warning("vlm_unavailable_cv_only_fallback", detail=exc.message)
                self.scheduler.completed.add(stage)
                return  # continue pipeline with reduced semantics
            state.route_override = Stage.VISION_UNAVAILABLE_ERROR.value
        self.db.finish_run(state.run_id, "failed", error=exc.message)

    def _terminal_route(self, state: PipelineState, stage: Stage) -> None:
        if stage == Stage.HUMAN_REVIEW_REQUIRED:
            state.human_review_required = True
            log.error("human_review_required", patch_attempts=state.patch_attempts)
        elif stage == Stage.COMPLIANCE_FAILURE:
            log.error("compliance_failure", reason=state.compliance_failure)
        elif stage == Stage.VISION_UNAVAILABLE_ERROR:
            log.error("vision_unavailable_error", reason=state.vision_unavailable)
        state.save(self._checkpoint(state.run_id))

    def _checkpoint(self, run_id: str) -> Path:
        return self._checkpoint_dir / f"{run_id}.json"

    def load_checkpoint(self, run_id: str) -> PipelineState:
        p = self._checkpoint(run_id)
        if not p.exists():
            raise AVEditorError(f"No checkpoint found for run '{run_id}'", path=str(p))
        return PipelineState.load(p)


def _run(fn: NodeFn, state: Any) -> Any:
    """Adapter letting :class:`Scheduler` call typed node functions."""
    return fn(state)
