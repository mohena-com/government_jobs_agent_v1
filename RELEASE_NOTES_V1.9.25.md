# V1.9.25 — Broad Recruitment Web Source Discovery

## Purpose

V1.9.25 removes the assumption that a government recruitment notification must be a PDF. The source-verification layer now supports PDF, HTML notification pages, plain-text endpoints, and HTML pages that link to the actual notification/application source.

## Changes

- Detect source format from response bytes/content-type instead of trusting `.pdf` extensions.
- Parse HTML recruitment notices with BeautifulSoup.
- Treat SarkariResult HTML as a discovery source rather than an authoritative notification.
- Automatically follow likely notification/advertisement/recruitment/PDF/application links discovered from HTML pages, up to a bounded depth.
- Recognise government/NIC/education domains as likely official hosts without blindly trusting them.
- Support generic HTML notices as verification anchors.
- Preserve every failed URL in the audit trail instead of allowing one bad auxiliary link to invalidate a valid source.
- Keep the existing RVUNL-specific reconciliation and authoritative profile unchanged.
- Keep the deterministic fact/quality gate: Qwen still receives only locked facts and is never allowed to invent missing values.
- Keep batch processing failure-isolated.
- Keep the existing slide QA and renderer unchanged.

## Source strategy

The verifier now uses a broad source-resolution strategy:

1. Fetch the supplied URL.
2. Detect PDF/HTML/text from the response itself.
3. Parse recruitment facts from HTML when present.
4. Discover relevant notification/advertisement/PDF links from HTML.
5. Follow discovered links within a bounded crawl depth.
6. Reconcile the resulting sources at field level.
7. Only then send verified/locked facts to Qwen.

This is deliberately not a general-purpose unrestricted web crawler. It is a bounded recruitment-source resolver designed to tolerate the common formats used by Indian government recruitment portals.

## Tests

57 passed.
