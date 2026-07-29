# Security

## Reporting

Found something? Email **jjpark324434@gmail.com**. This is a personal portfolio, not a
product — there is no bounty and no SLA, but I would rather hear about it than not.

## Design boundaries you should know about

**`codeguard.py` is not a sandbox.** The Data Analysis page lets an LLM generate pandas
code and executes it. The execution namespace is deliberately reduced — the `pandas`
module object is never exposed, dunder access and imports are rejected statically, `to_*`
writers are allowlisted rather than denylisted, and builtins are allowlisted — but there
is **no process isolation, no memory cap, and no wall-clock timeout**. It defends against
the escape paths a code-generating model actually reaches for, not against a determined
attacker. Three escapes have gotten through and been fixed; each is pinned as a test in
`tests/test_codeguard.py`. Assume more exist.

**The chatbot answers from a résumé injected into its system prompt.** Prompt-injection
guards (`guardrails.py`) run before the model, and the eval harness tests whether the
persona holds, but neither is a guarantee. Nothing secret is in that prompt.

## Known exposures, and what was decided about them

### Personal data in git history — present, not removed

Earlier versions of the résumé PDF committed to this repository contain a **phone number**
and a second personal e-mail address. An earlier commit message in this repo claims those
were *"purged from history"*. **That claim is incomplete and should not be relied on.**
The cleanup it describes covered the files at their current `assets/` paths but missed
copies committed under their original root-level paths, before the assets reorganisation.
The same applies to a pre-crop dashboard screenshot containing a GPU UUID.

This is being left in place deliberately, not overlooked:

- The exposure is a phone number that appears on the résumé sent to employers as a matter
  of course. It is not a credential, and rotating it is not comparable to rotating a key.
- This repository has been public for months. Rewriting history does not un-publish
  anything already cloned or crawled, and GitHub keeps unreferenced objects addressable by
  hash until they are purged by support request.
- Rewriting changes every commit hash in the repository, breaking every existing link into
  its history.

So the honest statement is the one above: **the history contains it, and the older commit
message overstates what was cleaned.** If that calculus changes, the fix is
`git filter-repo` over the affected paths followed by a force-push and a GitHub Support
request for the orphaned objects.

**Current state is clean**: the résumé served for download (`assets/resume.pdf`) and the
`resume_text` the chatbot answers from both carry the e-mail address only, no phone
number. The dashboard screenshot in `assets/` is the cropped one.

### Credentials

Deployment secrets (Groq API key, GCP service account, SMTP credentials) live in Streamlit
secrets and have never been committed. They were rotated on 2026-07-28 after a code
execution escape was found that could read the process environment; the escape is fixed
and pinned by a canary test that asserts no secret appears in a result *or* an error
string.

Anonymous visitors share one free-tier token budget, so chat is capped per session. That
cap is a courtesy limit — sessions reset when cookies are cleared — and is meant to stop
one visitor from exhausting the day's quota, not to stop an attacker.

### Sample data

`assets/tebo_sample.xlsx` contains human-subject posture measurements (numeric subject IDs
only, no direct identifiers). See `LICENSE` — it is included to make the demo runnable and
is not cleared for independent redistribution.
