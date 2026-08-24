# V1.9.31 — Multi-Job Prototype Stabilization

Fixes the prototype's three-job end-to-end path.

## Fixes
- Each generated Job Detail DOCX is processed independently.
- `--job-index 1` is used for every DOCX because each DOCX contains exactly one parsed job.
- Batch testing no longer passes the batch count as a per-DOCX job index.
- A failed job no longer prevents subsequent jobs from being attempted.
- Rendering occurs only when the corresponding Qwen JSON exists.
- Added a batch diagnostic helper.
- Retains the verification-to-generation decoupling behavior: missing/unavailable fields are fallbacks, while genuine factual conflicts remain blockers.
