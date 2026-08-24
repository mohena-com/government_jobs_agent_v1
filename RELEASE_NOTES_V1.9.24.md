# V1.9.24 — Generic Official-PDF Reconciliation

## Purpose

V1.9.24 fixes the batch failure pattern where the RVUNL job passed but most non-RVUNL jobs were blocked before Qwen.

## Changes

- SarkariResult-hosted **PDF documents are no longer skipped**. Only non-PDF SarkariResult detail/application pages are skipped.
- Official PDF downloading now retries, validates the PDF magic header, rejects cached HTML, and uses browser-like headers.
- Generic official-PDF extraction now recognizes more Indian recruitment date, age, vacancy, advertisement and section formats.
- Generic verification passes when at least one official PDF was successfully downloaded and parsed; a broken auxiliary URL is retained in the audit trail rather than poisoning the whole job.
- When a verified official PDF is available but a field is not machine-readable, the pipeline can preserve safe DOCX candidates or use an explicit “see official notification” value rather than inventing facts.
- Existing RVUNL specialised reconciliation remains unchanged.
- Qwen still cannot run when official verification itself fails.
- Batch processing remains failure-isolated.
- Slide QA and rendering are unchanged.

## Safety principle

The system never fabricates missing values. A field that cannot be safely extracted from the verified notification is explicitly marked for the official notification instead of being guessed.

## Tests

55 passed.
