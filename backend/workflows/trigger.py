"""
workflows/trigger.py

Called from main.py /run-attack route.
Triggers the camel_pipeline Render Workflow task
and streams results back via SSE.

Workflow slug format: {service-slug}/{task-name}
Get your workflow slug from Render Dashboard → your workflow service.
Set it as RENDER_WORKFLOW_SLUG env var.
"""

import os
from render import RenderAsync

WORKFLOW_SLUG = os.getenv("RENDER_WORKFLOW_SLUG", "payshield-workflow/camel_pipeline")


async def trigger_camel_workflow(
    user_instruction: str,
    context: dict,
    emit,
) -> dict:
    """
    Triggers camel_pipeline as a Render Workflow task.
    Streams trace steps back to the SSE bus via emit().
    Falls back to direct camel_agent.run() if workflow is unavailable.
    """
    try:
        render = RenderAsync()

        emit({"type": "step", "label": "workflow_started",
              "detail": "CaMeL pipeline dispatched to Render Workflows"})

        task_run = await render.workflows.run_task(
            WORKFLOW_SLUG,
            {"user_instruction": user_instruction, "context": context},
        )

        # Stream trace steps from workflow result back to SSE
        if task_run.results:
            result = task_run.results[0]
            for step in result.get("trace", []):
                emit(step)

        emit({"type": "step", "label": "workflow_completed",
              "detail": f"run_id: {task_run.id}"})

        return result if task_run.results else {}

    except Exception as e:
        # Fallback to direct execution if workflow is unavailable
        emit({"type": "step", "label": "workflow_fallback",
              "detail": f"Workflow unavailable ({e}), running directly"})

        from backend.agents.camel_agent import run as camel_run
        camel_run(user_instruction, context, emit)
        return {}