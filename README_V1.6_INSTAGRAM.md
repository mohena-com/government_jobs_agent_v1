# V1.6 — Curated Instagram Recruitment Slides

The Instagram generator has been redesigned around the supplied reference
style: a professional government-recruitment infographic rather than a
generic text dump.

## Principles

- Only display fields that contain useful extracted information.
- Never display "Not found", N/A, empty headings, or placeholder columns.
- Do not create a vacancy slide if no structured vacancy rows exist.
- Do not create a links slide if no usable URL exists.
- Do not create an eligibility section if eligibility data is missing.
- Remove social/navigation garbage and common SarkariResult boilerplate.
- Keep the most important information visually prominent:
  organisation, post, deadline, vacancies, eligibility, fee, pay, dates and
  official links when actually available.
- Use a 1080 x 1350 (4:5) Instagram canvas.
- Slide count is dynamic; sparse jobs get fewer slides.

## Run

```bash
python main.py --max-jobs 3 --instagram
```

Output:

```text
social/instagram/
  01_<job>/
    01_*.png
    02_*.png
    ...
```

The design uses a clean navy/white/yellow government-recruitment visual
language inspired by the supplied reference image, without assuming data that
is not present in the crawled recruitment record.
