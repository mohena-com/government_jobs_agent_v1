# V1.9.17 — Creative Instagram Presentation Layer

V1.9.17 upgrades only the presentation layer. The official-PDF verification,
locked-fact model, Qwen positional contract, source quality gate and slide-level
quality gate remain intact.

## What changed

- Replaced the report-like Qwen renderer with a recruitment-poster presentation engine.
- Added specialized visual layouts for all six fixed slide types:
  1. Hero recruitment hook
  2. Post-wise vacancy table
  3. Post-wise eligibility cards
  4. Age + pay + application-fee stat cards
  5. Application timeline + selection process
  6. Apply CTA + QR codes for official sources
- Renderer uses locked/verified facts for high-risk numeric information wherever possible.
- Long URLs are never printed in artwork. They are represented by human-friendly labels,
  official domains and QR codes.
- Added a stronger presentation sanitizer that removes audit/debug leakage such as
  PASS/FAIL, quality gate, reconciliation, extraction repairs, parsed/authoritative
  vacancies, locked facts, PDF extraction notes and Qwen metadata.
- Added organisation monogram branding when no verified logo asset is available.
- Added poster-style visual hierarchy: hero numbers, accent ribbons, stat cards,
  timeline, CTA strips and alternating vacancy rows.
- Kept 1080x1350 (4:5) Instagram dimensions.
- No facts are invented by the renderer; missing facts are represented conservatively.

## Rendering

```bash
python3 main.py \
  --render-qwen social/qwen_v1917/qwen_instagram_plans.json \
  --render-output social/rendered_v1917 \
  --job-index 1
```

The presentation JSON remains:

```text
social/qwen_v1917/instagram_presentation_ready.json
```

The audit JSON remains:

```text
social/qwen_v1917/qwen_instagram_plans.json
```
