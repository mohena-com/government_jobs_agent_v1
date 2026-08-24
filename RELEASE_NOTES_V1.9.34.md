# V1.9.34 — Application Date Presentation Hotfix

## Problem
The semantic application dates could be present in the validated six-slide plan,
while the renderer's `locked_facts.application_start/application_end` fields were
blank or stale. Slide 5 therefore rendered "See official notification" even though
the plan contained the correct application window.

## Fix
`src/social/qwen_renderer.py` now resolves Slide 5 application dates in this order:

1. semantic locked `application_start` / `application_end`
2. explicit `Application Start` / `Application Deadline` bullets in the validated slide plan
3. compact `Apply Online: START – END` presentation copy

Fee-payment and exam dates are never treated as application dates by this resolver.

## Result
A plan containing:
- Application Start: 28 July 2026
- Application Deadline: 27 August 2026

now renders those exact dates in the Slide 5 timeline.

## Regression
Rendered the supplied Patna High Court plan successfully and verified that Slide 5
displays:
- APPLICATION OPENS — 28 July 2026
- LAST DATE TO APPLY — 27 August 2026
