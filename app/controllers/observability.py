from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..core.dependencies import get_current_user
from ..models.user import User
from ..ai.observability import get_store
from ..schemas.observability import ObservabilitySummary, ObservabilityTracesResponse

router = APIRouter(prefix="/observability", tags=["Observability"])

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Vacation Planner Observability</title>
  <style>
    :root { color-scheme: dark; }
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 24px 32px; border-bottom: 1px solid #1e293b; }
    h1 { margin: 0 0 6px; font-size: 22px; }
    p { margin: 0; color: #94a3b8; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; padding: 24px 32px; }
    .card { background: #1e293b; border-radius: 12px; padding: 16px 18px; }
    .label { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #94a3b8; }
    .value { font-size: 28px; font-weight: 700; margin-top: 8px; }
    table { width: calc(100% - 64px); margin: 0 32px 32px; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
    th, td { text-align: left; padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; font-weight: 600; }
    .ok { color: #4ade80; }
    .bad { color: #f87171; }
  </style>
</head>
<body>
  <header>
    <h1>AI Vacation Planner</h1>
    <p>Latency, tokens, model, errors, and failed requests · __SERVICE__ / __ENV__</p>
  </header>
  <section class="grid">
    <div class="card"><div class="label">Requests</div><div class="value">__REQUESTS__</div></div>
    <div class="card"><div class="label">Avg latency</div><div class="value">__LATENCY__ ms</div></div>
    <div class="card"><div class="label">Tokens</div><div class="value">__TOKENS__</div></div>
    <div class="card"><div class="label">Errors</div><div class="value">__ERRORS__</div></div>
    <div class="card"><div class="label">Failed requests</div><div class="value">__FAILED__</div></div>
    <div class="card"><div class="label">Blocked</div><div class="value">__BLOCKED__</div></div>
  </section>
  <table>
    <thead>
      <tr><th>Span</th><th>Model</th><th>Latency</th><th>Tokens</th><th>Status</th></tr>
    </thead>
    <tbody>__ROWS__</tbody>
  </table>
</body>
</html>
"""


@router.get(
    "/metrics",
    response_model=ObservabilitySummary,
    summary="Agent observability counters",
    description="In-process counters for planning latency, token usage, errors, and failed requests. When DATADOG_ENABLED=true these also go to DogStatsD.",
)
def observability_metrics(current_user: User = Depends(get_current_user)):
    del current_user
    return get_store().summary()


@router.get(
    "/traces",
    response_model=ObservabilityTracesResponse,
    summary="Recent AI planning traces",
    description="Recent plan_trip spans including model, latency, token usage, and errors.",
)
def observability_traces(current_user: User = Depends(get_current_user)):
    del current_user
    store = get_store()
    return {"summary": store.summary(), "traces": store.recent()}


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Local observability dashboard",
    description="Screenshot-friendly dashboard for latency, tokens, model, errors, and failed requests. Import data/observability/datadog-dashboard.json into Datadog for the hosted version.",
)
def observability_dashboard(current_user: User = Depends(get_current_user)):
    del current_user
    store = get_store()
    summary = store.summary()
    rows = []
    for trace in store.recent(12):
        status = '<span class="bad">failed</span>' if trace.get("failed") else '<span class="ok">ok</span>'
        rows.append(
            "<tr>"
            f"<td>{trace.get('name') or ''}</td>"
            f"<td>{trace.get('model') or '—'}</td>"
            f"<td>{trace.get('latency_ms') if trace.get('latency_ms') is not None else '—'} ms</td>"
            f"<td>{trace.get('total_tokens') or 0}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    html = (
        _DASHBOARD_HTML.replace("__SERVICE__", str(summary["service"]))
        .replace("__ENV__", str(summary["env"]))
        .replace("__REQUESTS__", str(summary["requests"]))
        .replace("__LATENCY__", str(summary["average_latency_ms"]))
        .replace("__TOKENS__", str(summary["total_tokens"]))
        .replace("__ERRORS__", str(summary["errors"]))
        .replace("__FAILED__", str(summary["failed_requests"]))
        .replace("__BLOCKED__", str(summary["blocked_requests"]))
        .replace("__ROWS__", "".join(rows) or "<tr><td colspan='5'>No traces yet. Generate a plan first.</td></tr>")
    )
    return HTMLResponse(html)
