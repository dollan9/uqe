"""
UQE Reporter — Evidence Visualization & Dashboard Generator
"""

import json
import html
from pathlib import Path
from typing import Dict, Any

def generate_html_report(data: Dict[str, Any], title: str = "UQE Evidence Report") -> str:
    task = html.escape(str(data.get("task", "Unknown Task")))
    tier = html.escape(str(data.get("tier", "T1")))
    generated_at = html.escape(str(data.get("generated_at", "N/A")))
    evidence_items = data.get("evidence", [])
    defects = data.get("defects", [])
    scores = data.get("scores", {})
    unverified = data.get("unverified_claims", [])

    # Calculate overall health
    critical_defects = [d for d in defects if d.get("severity") == "critical" and d.get("status") != "fixed"]
    has_critical = len(critical_defects) > 0
    status_text = "REJECTED (Critical Defects Open)" if has_critical else "VERIFIED"
    status_bg = "#ef4444" if has_critical else "#10b981"

    # Score bars
    scores_html = ""
    for k, v in scores.items():
        pct = int((v / 10.0) * 100)
        bar_color = "#10b981" if v >= 8 else ("#f59e0b" if v >= 6 else "#ef4444")
        scores_html += f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 4px;">
                <span style="font-weight: 500; color: #cbd5e1;">{html.escape(k)}</span>
                <span style="font-weight: 600; color: #f8fafc;">{v}/10</span>
            </div>
            <div style="background: #334155; border-radius: 9999px; height: 8px; overflow: hidden;">
                <div style="background: {bar_color}; width: {pct}%; height: 100%; border-radius: 9999px;"></div>
            </div>
        </div>
        """

    # Evidence items
    evidence_html = ""
    for idx, e in enumerate(evidence_items):
        etype = html.escape(str(e.get("type", "other")))
        epath = html.escape(str(e.get("path", "")))
        eobserved = html.escape(str(e.get("observed", "")))
        etool = html.escape(str(e.get("tool", "unspecified")))
        equality = html.escape(str(e.get("quality", "E2")))
        badge_bg = "#0284c7" if equality == "E3" else ("#0d9488" if equality == "E2" else "#64748b")

        evidence_html += f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: #3b82f6; color: #fff; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{etype.upper()}</span>
                    <span style="background: {badge_bg}; color: #fff; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{equality}</span>
                    <code style="color: #38bdf8; font-size: 0.875rem;">{epath}</code>
                </div>
                <span style="font-size: 0.75rem; color: #94a3b8;">tool: {etool}</span>
            </div>
            <div style="font-size: 0.875rem; color: #e2e8f0; line-height: 1.5; background: #0f172a; padding: 10px; border-radius: 6px; border-left: 3px solid #38bdf8;">
                <strong>Observed:</strong> {eobserved}
            </div>
        </div>
        """

    # Defects HTML
    defects_html = ""
    if defects:
        for d in defects:
            dsev = html.escape(str(d.get("severity", "minor")))
            ddesc = html.escape(str(d.get("description", "")))
            dstatus = html.escape(str(d.get("status", "open")))
            sev_color = "#ef4444" if dsev == "critical" else ("#f97316" if dsev == "major" else "#eab308")
            status_color = "#10b981" if dstatus == "fixed" else "#f43f5e"

            defects_html += f"""
            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="background: {sev_color}; color: #fff; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">{dsev.upper()}</span>
                    <span style="font-size: 0.875rem; color: #f1f5f9;">{ddesc}</span>
                </div>
                <span style="background: {status_color}22; color: {status_color}; border: 1px solid {status_color}; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{dstatus.upper()}</span>
            </div>
            """
    else:
        defects_html = """
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; color: #94a3b8; font-size: 0.875rem;">
            No defects recorded. Verification completed cleanly.
        </div>
        """

    # Unverified claims HTML
    unverified_html = ""
    if unverified:
        for u in unverified:
            uclaim = html.escape(str(u.get("claim", "")))
            ureason = html.escape(str(u.get("reason", "")))
            umanual = html.escape(str(u.get("manual_check", "")))
            unverified_html += f"""
            <div style="background: #451a03; border: 1px solid #b45309; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
                <div style="font-size: 0.875rem; font-weight: 600; color: #fde68a;">Claim: {uclaim}</div>
                <div style="font-size: 0.8125rem; color: #fef3c7; margin-top: 4px;">Reason: {ureason}</div>
                {f'<div style="font-size: 0.8125rem; color: #cbd5e1; margin-top: 6px;"><code>{umanual}</code></div>' if umanual else ''}
            </div>
            """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — {task}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0b1120;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            padding: 24px;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .header {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .badge {{
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: #141e33;
            border: 1px solid #283548;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .footer {{
            text-align: center;
            font-size: 0.8125rem;
            color: #64748b;
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #1e293b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span class="badge" style="background: #6366f1; color: #fff;">UQE {tier}</span>
                    <span style="font-size: 0.875rem; color: #94a3b8;">Universal Quality Engine</span>
                </div>
                <h1 style="font-size: 1.5rem; font-weight: 700; color: #fff;">{task}</h1>
                <div style="font-size: 0.8125rem; color: #94a3b8; margin-top: 6px;">Generated at: {generated_at}</div>
            </div>
            <div>
                <span class="badge" style="background: {status_bg}; color: #fff; font-size: 0.875rem; padding: 6px 14px;">{status_text}</span>
            </div>
        </div>

        <div class="grid">
            <!-- Left Column: Evidence & Defects -->
            <div>
                <div class="card">
                    <div class="card-title">
                        <span>Inspectable Evidence Artifacts</span>
                        <span style="font-size: 0.875rem; color: #38bdf8;">{len(evidence_items)} recorded</span>
                    </div>
                    {evidence_html}
                </div>

                <div class="card">
                    <div class="card-title">
                        <span>Adversarial Self-Critique & Defects</span>
                        <span style="font-size: 0.875rem; color: #94a3b8;">{len(defects)} total</span>
                    </div>
                    {defects_html}
                </div>

                {f'''
                <div class="card" style="border-color: #b45309;">
                    <div class="card-title" style="color: #fde68a;">
                        <span>Honest Disclosures & Unverified Claims</span>
                    </div>
                    {unverified_html}
                </div>
                ''' if unverified else ''}
            </div>

            <!-- Right Column: Scores & Policy -->
            <div>
                <div class="card">
                    <div class="card-title">Quality Dimension Scores</div>
                    {scores_html if scores else '<div style="color: #64748b; font-size: 0.875rem;">No dimension scores defined.</div>'}
                </div>

                <div class="card" style="background: #0f172a; border-color: #1e293b;">
                    <div class="card-title" style="font-size: 0.95rem; color: #94a3b8;">The Prime Directive</div>
                    <p style="font-size: 0.8125rem; color: #cbd5e1; font-style: italic; line-height: 1.6;">
                        "Assume nothing. Verify everything. Use the cheapest sufficient evidence. Do not ship blind. Do not fabricate. Do not over-process trivial work."
                    </p>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated with UQE v3.2.0 • Evidence-Backed Engineering Standard
        </div>
    </div>
</body>
</html>"""
