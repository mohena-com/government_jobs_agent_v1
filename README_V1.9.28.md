# V1.9.28 — Professional Six-Slide Instagram Creative Engine

This release keeps the proven six-slide information architecture and makes the presentation layer more like a trained Instagram recruitment designer.

## Six slides
1. Hero / Recruitment
2. Post-wise Vacancies
3. Who Can Apply?
4. Age + Pay + Application Fee
5. Important Dates + Selection
6. Ready to Apply / Documents / Official Links

## Visual language
- Navy/blue section bars
- Yellow/gold sub-bars and highlight chips
- Large numeric emphasis
- Compact card grids
- Consistent masthead and footer
- Human-readable dates
- QR/short official-link treatment instead of raw URLs
- Content-fit wording; no notification paragraphs on artwork

## Source verification behavior
Official-source verification remains an audit signal. In presentation/batch mode, a partial verification failure does not globally block Qwen. The model is constrained to extracted facts and must use “Refer to Official Notification” when a field is unavailable.

## Prompt
The active prompt is `prompts_instagram_v1.9.28.txt` and can be overridden with `--qwen-prompt`.

## Shell scripts
Existing shell orchestration is intentionally left unchanged. The active prompt and Python presentation layer are updated without requiring `.sh` changes.
