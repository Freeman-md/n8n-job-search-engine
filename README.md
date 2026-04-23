# Job Automation Engine

> A modular, state-driven n8n pipeline that discovers LinkedIn jobs, scores fit, enriches company context, extracts hiring contacts, and generates tailored CV and cover letter artifacts — delivering an action-ready application package to Slack.

## Project Metadata
- Type: system
- Domain: Automation / AI Pipelines / Job Search
- Status: v1.0 — functional, open sourced with sanitized exports
- Level: advanced
- Year: 2026
- Featured: true
- Repository URL: Not public
- Live URL: Not deployed
- Thumbnail URL:

## Summary

The Job Automation Engine is a nine-workflow n8n system that automates the full job application preparation pipeline. It ingests a CV via an upload form, extracts structured candidate data, and generates multiple differentiated profile variants using OpenAI. From there, it runs on a weekday schedule: discovering fresh LinkedIn jobs via Apify, routing each job through a status-driven pipeline, extracting job details, scoring fit against the candidate profile, enriching company intelligence, pulling likely hiring contacts, tailoring a CV and cover letter per role, and finally sending a Slack notification with direct links to apply.

All intermediate artifacts are persisted as text snapshots in Google Drive and tracked in Airtable. The pipeline is inspectable at every stage. No job reaches the tailoring stage unless it has cleared the fit scoring gate.

## Tech Stack

- n8n (workflow orchestration)
- Airtable (state store, relational working database)
- OpenAI GPT-5 Mini (profile extraction, search config generation, job detail extraction, fit scoring, company intelligence, CV tailoring, cover letter generation)
- Apify (`harvestapi/linkedin-job-search`, `harvestapi/linkedin-profile-scraper`, `apimaestro/linkedin-company-employees-scraper-no-cookies`)
- Google Drive (CV upload, per-job folder creation, text file snapshots)
- Slack (final `READY_TO_APPLY` notification with apply, CV, and cover letter buttons)
- Python 3 (sanitization script for workflow exports)

## System Context

Job searching at volume produces two failure modes: applying to roles that are a poor fit, and writing generic application materials that don't reflect the specific role. This pipeline addresses both by treating job search as a controlled data pipeline with explicit state transitions, a fit gate that blocks weak matches before any tailoring work begins, and AI-generated application assets grounded in real job data, real company context, and the candidate's actual CV.

The design intentionally constrains search volume (maximum 14 raw results per daily run) to prioritize signal over surface area. The operator reviews and applies manually — the pipeline's job is to deliver a curated, fully prepared package for each viable opportunity.

## System Snapshot

### Core System Idea

Jobs enter the pipeline as `LISTED` records in Airtable. A status webhook on the Jobs table fires Workflow 2 on every status change. Workflow 2 reads the current status and calls the appropriate downstream workflow. Each downstream workflow validates its inputs, performs its work, writes outputs to Airtable and Google Drive, and advances the job to the next status. The cycle repeats until the job reaches `READY_TO_APPLY` or is marked `REJECTED`.

### Main Components

1. **Workflow 0 — User Profile Generation**: Accepts a PDF CV via an n8n form trigger, extracts text, uploads the file to Google Drive, and runs two sequential OpenAI agents — one to build a canonical profile, one to generate multiple strategically differentiated profile variants. Each variant is split and saved as a separate Airtable `Profile` record with fields for type, summary, skills, preferences, visa constraints, and locations.

2. **Workflow 1 — Job Discovery**: Runs on a weekday schedule. Loads active profiles from Airtable, selects one per day via day-of-week rotation, calls an OpenAI agent to generate two LinkedIn search configs (scoped to UK, full-time, tech industry IDs 4/5/6, `maxItems = 7` each), validates the configs via a subflow, fetches jobs from Apify, deduplicates by job ID and company, upserts company records, and creates `Job` records at status `LISTED`.

3. **Workflow 2 — Job Status Router**: Receives Airtable webhook events on every job status change. Validates the payload, re-reads the canonical job record from Airtable, and routes to the correct downstream workflow via a Switch node. Covers all six active transitions: `LISTED` → `DETAILED` → `SCORED` → `COMPANY_ENRICHED` → `CONTACTS_FOUND` → `TAILORED` → `READY_TO_APPLY`.

4. **Workflows 3–7 — Pipeline Stages**: Each workflow is a self-contained execution unit triggered by Workflow 2. They validate their inputs against the expected precondition status, call OpenAI or Apify as required, write structured text snapshots to Google Drive, create `Document` records in Airtable, and advance the job status on completion.

5. **Workflow 8 — Application Ready Notification**: Validates that tailored CV and cover letter documents exist, merges job metadata (title, company, location, fit score, visa risk, application type), and sends a structured Slack block message with fit score label (High / Medium / Low), role details, and action buttons for Apply, View CV, and View Cover Letter. Sets the job to `READY_TO_APPLY`.

6. **Subflows**: `OpenAI Response Validator & Payload Extractor` validates and unwraps OpenAI structured output responses from the `output[0].content[0].text` path. `Google Drive File Content Retrieval` downloads a file by ID, detects whether it is PDF or plain text, and returns extracted text content.

## Design Focus

- State is the single source of truth. Every workflow reads and writes Airtable status fields. No workflow proceeds unless the incoming status matches its expected precondition.
- AI usage is split by intent. Extraction agents (Workflows 0, 3) are strict and conservative — they return null rather than infer. Scoring (Workflow 4) is conservative and defensible. Tailoring (Workflow 7) is assertive, but only after the fit gate passes.
- Search volume is hard-capped at the schema level. The Search Construction Agent is constrained to produce exactly two configs with `maxItems = 7` each, making the daily ceiling 14 raw results.
- All AI outputs are persisted as human-readable `.txt` snapshots in Google Drive, making the pipeline auditable without querying Airtable directly.
- Shared logic is extracted into reusable subflows. OpenAI response validation and Google Drive file retrieval are called from multiple parent workflows rather than duplicated.

## Architectural Innovation

The core architectural decision is using Airtable status field changes as the inter-workflow communication mechanism. Rather than chaining workflows directly or using a queue, each workflow writes a new status to Airtable, which fires the webhook trigger on Workflow 2, which routes to the next stage. This means the pipeline can be paused, inspected, restarted, or manually advanced by editing a status field in Airtable — no n8n intervention required. Any job record in the right status can trigger its downstream workflow without replaying the full pipeline from the start.

The fit scoring gate in Workflow 4 enforces a hard threshold before enrichment or tailoring begins. Jobs pass only if `skill_alignment_score >= 0.55`, or if `overall_fit_score >= 0.6` and `skill_alignment_score >= 0.45`. All other jobs are marked `REJECTED` with a scoring reason field populated. This prevents enrichment and tailoring compute from running on weak matches.

## Implementation Model

Workflow 0 is triggered manually via an n8n form URL. Workflow 1 runs on a scheduled trigger (Monday–Friday at 09:00). All subsequent workflows are triggered by Airtable webhook events routed through Workflow 2's webhook endpoint. The webhook payload carries the Airtable record ID and current status. Workflow 2 re-reads the full record from Airtable before routing, so it always operates on fresh data regardless of what the webhook body contains.

Each stage workflow uses a `Validate Inputs` Code node as its first step. These validators throw explicit errors with field-level messages if required inputs are missing or the status does not match the expected precondition, surfacing failure modes clearly in the n8n execution log.

OpenAI calls use the Responses API (`@n8n/n8n-nodes-langchain.openAi`) with `json_schema` structured output, `additionalProperties: false`, and `strict: true` on all schemas. The `OpenAI Response Validator & Payload Extractor` subflow handles the response unwrapping and throws if the response status is not `"completed"`. Per-job documents are created in Google Drive folders named `{Job Title} - {Company} - {Job ID}` to keep artifacts organized and traceable.

## Performance / Operational Profile

### Latency Profile
- Title: Per-job pipeline latency is minutes, not seconds
- Description: Each stage involves at least one OpenAI API call and one or more Airtable reads and writes. Workflow 7 (tailoring) makes four sequential OpenAI calls. End-to-end latency from `LISTED` to `READY_TO_APPLY` for a passing job is approximately 5–10 minutes under normal API conditions. The pipeline runs asynchronously via webhook chaining, so multiple jobs can be in-flight simultaneously at different stages.

### System Focus
- Title: Correctness over throughput; operator applies manually
- Description: The pipeline is designed for daily, curated throughput — not bulk processing. The hard cap of 14 raw job results per day is intentional. The operator receives a Slack notification for each job that reaches `READY_TO_APPLY` and makes the final application decision manually. The system does not auto-apply.

## Outcomes

- Full pipeline functional across Workflows 0–8, covering the complete status progression from `LISTED` to `READY_TO_APPLY`
- Fit scoring gate enforced: jobs below threshold are marked `REJECTED` with a populated scoring reason before enrichment or tailoring runs
- Per-job Google Drive folder created automatically, containing `Job_Info.txt`, `Company_Info.txt`, `CV_Info.txt`, and `Cover_Letter_Info.txt`
- Slack notification delivers a structured block message with fit score label, job metadata, visa risk, application type, and direct action buttons per application package
- Sanitization script strips all private identifiers from workflow exports while preserving node structure, prompts, routing logic, and architecture

## Why This Matters

Job application pipelines without a fit gate waste compute and time generating tailored materials for roles that are poor matches. This system enforces the gate explicitly and makes the decision trail visible: every rejected job has a scoring reason, every passing job has a full document trail in Google Drive. The operator can audit any artifact before applying and can manually advance or halt any job in the pipeline by editing an Airtable field. The modular workflow structure means individual stages can be replaced, upgraded, or tested independently without touching the rest of the pipeline.

## Future Improvements

- Automated Airtable schema provisioning (currently must be created manually before import)
- Bootstrap script for Google Drive folder structure, Slack channel setup, and credential scaffolding
- Hardening of fallback branches in Workflow 6 when no hiring contacts are found (currently routes to a NoOp placeholder pending Slack integration)
- Additional job sources beyond LinkedIn (Indeed, company career pages)
- Idempotency guard on Workflow 2 to prevent duplicate downstream executions if the webhook fires more than once for the same status transition
- Cover letter output as a formatted Google Doc or PDF rather than a plain text snapshot

## Repository Contents

- `workflows/` — main workflow JSON exports (Workflows 0–8)
- `workflows/subflows/` — helper workflow exports (`OpenAI Response Validator & Payload Extractor`, `Google Drive File Content Retrieval`)
- `scripts/sanitize_n8n_exports.py` — strips private execution data and local identifiers from workflow exports before publishing

## Before You Import

- Create your own credentials in n8n for OpenAI, Airtable, Google Drive, Apify, and Slack
- Recreate the Airtable schema to match the tables and fields used in the exports: `Jobs`, `Profile`, `Companies`, `Contacts`, `Document`
- Reconnect subflows after import by replacing `<link-this-workflow>` references with your actual workflow IDs in n8n
- Point Google Drive nodes to your own folder IDs (replace `<configure-in-your-instance>` values)
- Point Slack nodes to your own channel
- Review all prompts and scoring thresholds before running against real applications
- Run `python3 scripts/sanitize_n8n_exports.py` before publishing any future export updates

## What Was Sanitized

- Pinned execution data
- Credential IDs
- Webhook IDs
- Airtable base, table, and resource IDs
- Google Drive folder and file IDs
- Slack channel IDs and webhook IDs
- n8n instance metadata and workflow version IDs

Node structure, routing logic, system prompts, scoring thresholds, and overall architecture were kept intact.

## Open Source Status

This repository is open sourced as a working personal automation system, not as a polished product. It handles the main path well. Some fallback branches and edge cases still need hardening for a fully production-grade deployment.
