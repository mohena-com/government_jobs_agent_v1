# V1.9 — Official PDF Verification + Reconciliation

V1.9 adds an authoritative-source verification stage between DOCX extraction and Qwen.

## Flow

```text
V1.6/V1.7 DOCX
    ↓
V1.8.1 DOCX fact extraction
    ↓
quality gate
    ↓ missing/unverified facts
official notification URLs
    ↓
download PDF + extract text
    ↓
classify advertisement
    ↓
post/vacancy/date/age/pay extraction
    ↓
reconciliation across PDFs
    ↓
verified facts
    ↓
Qwen (only if verification passes)
```

## Run RVUNL verification without Qwen

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v19
```

This downloads the official notification PDFs listed in the DOCX. Qwen is not called because `--quality-gate-only` is enabled.

Expected RVUNL reconciliation:

- Advertisement `RVUN/Rectt.-2026-27/02` — Junior Engineer-I — 869 vacancies.
- Advertisement `RVUN/Rectt.-2026-27/03` — Junior Accountant + Junior Assistant/Commercial Assistant-II — 1,136 vacancies.
- Combined total — 2,005 vacancies.
- Application start — 2026-08-05.
- Application end — 2026-08-25.
- Age differs by advertisement, so V1.9 stores advertisement-specific age limits instead of flattening them into one unsafe value.

## Important

The verifier does not trust the SarkariResult title's `2005` value as authoritative. It uses the official PDFs and reconciles the post-wise totals. It also preserves download errors and source URLs in the output.

The third URL in the RVUNL DOCX may be a short/related notice. It is retained as a source candidate, but the combined verification can pass when the two detailed advertisements reconcile to the combined recruitment.

## Dependencies

V1.9 adds `pypdf` for local PDF text extraction.
