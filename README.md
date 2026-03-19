# Job Automation Engine

This repository contains a modular n8n job-search pipeline built around controlled state transitions instead of one large workflow.

The system ingests a CV, creates reusable profile variants, discovers jobs, enriches and scores them, pulls hiring contacts, tailors application assets, and sends a final notification when an application package is ready to review.

## What It Is

- `Workflow 0`: upload a CV, extract structured candidate data, and generate targeted profile variants
- `Workflow 1`: discover fresh LinkedIn jobs from profile-driven search configs
- `Workflow 2`: route every job through state-based downstream execution
- `Workflow 3`: extract structured job details and store a job snapshot
- `Workflow 4`: score job-to-profile fit and reject weak matches
- `Workflow 5`: generate company intelligence for stronger application context
- `Workflow 6`: pull likely hiring contacts from LinkedIn company/profile data
- `Workflow 7`: tailor CV and cover letter artifacts from job, company, and CV context
- `Workflow 8`: send a final action-ready notification with application links
- `subflows`: helper workflows for OpenAI payload validation and Google Drive file text retrieval

## Stack

- `n8n` for orchestration
- `Airtable` as the state store and working database
- `Google Drive` for file snapshots and intermediate artifacts
- `OpenAI` for extraction, scoring, and document generation
- `Apify` for LinkedIn job and profile scraping
- `Slack` for the final operator notification

## Design Notes

- The pipeline is state-driven. Jobs move through statuses such as `LISTED`, `DETAILED`, `SCORED`, `COMPANY_ENRICHED`, `CONTACTS_FOUND`, `TAILORED`, and `READY_TO_APPLY`.
- The AI usage is split by responsibility. Extraction and scoring are strict and conservative. Tailoring is more assertive, but only after the fit gate passes.
- Artifacts are persisted as text snapshots so the system stays inspectable.
- Search volume is intentionally constrained to avoid broad low-signal scraping.

## Repository Contents

- `workflows/`: main workflow exports
- `workflows/subflows/`: helper workflow exports used by the main flows
- `scripts/sanitize_n8n_exports.py`: removes private execution data and local identifiers from exported workflows

## Open Source Status

This repository is open sourced as a working personal automation system, not as a polished SaaS product.

It handles the main path well, but it is not presented as fully production-grade. Some edge cases and operator fallback flows still need hardening.

## What Was Sanitized

- pinned execution data
- credential ids
- webhook ids
- Airtable, Google Drive, Slack, and workflow instance ids used for local wiring
- local instance metadata

The workflow names, node structure, prompts, routing logic, and overall architecture were kept intact.

## Before You Import It

- create your own credentials in n8n
- recreate the Airtable schema to match the fields used in the exports
- reconnect any helper subflows after import
- point Google Drive nodes to your own folders
- point Slack nodes to your own channel
- review all prompts and thresholds before running against real applications
- rerun `python3 scripts/sanitize_n8n_exports.py` before publishing any future export updates

## Known Limitations

- Some fallback branches are still operator-oriented rather than fully automated
- The Airtable schema is assumed rather than provisioned automatically
- The exports do not include a one-click bootstrap for tables, folders, and credentials
- LinkedIn and enrichment dependencies are third-party services and may change behavior or pricing

## Why This Exists

The goal was not to auto-apply everywhere.

The goal was to control the pipeline:

- decide what gets discovered
- decide what gets rejected
- keep the decision trail visible
- generate tailored assets only for roles worth the effort

## Publishing Notes

The repository is prepared for public publishing with an MIT license and sanitized workflow exports.
