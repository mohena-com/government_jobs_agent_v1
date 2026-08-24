# V1.9.26 — Two-Slide Presentation Layer

- Replaced the six-slide Qwen presentation contract with an exact two-slide contract based on the supplied presentation prompt.
- Slide 1: Vacancy & Eligibility + Age Limit + Selection Process.
- Slide 2: Pay & Salary + Application Fee + Important Dates + Documents/Instructions.
- Common masthead, quick-info bar and footer are rendered consistently on both slides.
- Long qualifications and prose are condensed for visual fit; unreadable font shrinking is avoided.
- Raw URLs are never rendered as long text; structured official links may be represented by a QR/domain label.
- Slide QA now validates exactly two slide types: `job_details` and `at_a_glance`.
- Batch generation now expects and renders two PNGs per job.
- Existing source verification, locked-facts, sanitization and batch isolation remain intact.
