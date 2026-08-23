# SarkariResult V1.5 — Instagram Carousel Generator

V1.5 adds code-based Instagram carousel generation to the SarkariResult-only
government jobs agent.

## Output

For every crawled recruitment, the agent creates a 5-slide Instagram carousel:

1. Job title + organisation + application deadline
2. Key information
3. Vacancy details
4. Eligibility + application fee
5. Official notification/application links + source

Canvas size:

`1080 x 1350` — Instagram 4:5 portrait format.

## Run

Normal reports:

```bash
python main.py --max-jobs 3
```

Reports + Instagram slides:

```bash
python main.py --max-jobs 3 --instagram
```

Optional output location:

```bash
python main.py --max-jobs 3 --instagram --social-dir social/instagram
```

## Output structure

```text
reports/
├── SarkariResult_LatestJobs_YYYY-MM-DD_Summary.docx
└── jobs/
    ├── 01_....docx
    ├── 02_....docx
    └── ...

social/
└── instagram/
    ├── 01_<job>/
    │   ├── 01_<job>.png
    │   ├── 02_<job>.png
    │   ├── 03_<job>.png
    │   ├── 04_<job>.png
    │   └── 05_<job>.png
    ├── 02_<job>/
    └── ...
```

The generator removes common SarkariResult social/navigation artefacts such as
Telegram, Join Us, WhatsApp, Instagram, Follow, X and image placeholders.

It uses only the structured job data already extracted by the crawler; it does
not invent missing job details.
