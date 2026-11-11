# Track 1 — New bug discovery report

Date: 2026-11-10. Environment: Windows 10 build 19045, Python 3.15.2, installed UnvibeCode 0.4.0 (`Requires-Python: >=3.11`). The installed package, prior evidence, original fixtures, and source repositories were not modified. New investigation artifacts are confined to this directory.

## Executive decision

One new client defect was reproduced: a malformed or early-EOF final result ZIP escapes the CLI's normal error handler as an uncaught `zipfile.BadZipFile`. The completed job's output is not extracted, the process exits 1 with a traceback, and the CLI does not print its documented resume command even though the job ID is already known internally. A valid result ZIP control succeeds.

This is a concrete, distinct client failure, but it is conditional on a malformed/truncated successful HTTP response. It may be more disruptive to workflow completion than the Unicode redraw issue, but it does **not** clearly exceed the junction candidate's potential out-of-repository data exposure. Therefore, no new finding is established as stronger than both existing findings.

## Environment and source provenance

- Installed package path: `%APPDATA%\Python\Python315\site-packages\unvibecode`.
- Package version and CLI entry point were verified from installed metadata: `0.4.0`, `unvibecode = unvibecode.cli:main`.
- The package metadata README documents the commands and result handling described below.
- The public GitHub repository `FinanceFlash/unvibecode` was inspected using read-only file, code, issue, PR, and commit searches. Its default-branch `README.md` is available, but fetching `pyproject.toml` and the installed module paths (`unvibecode/client.py`, `unvibecode/cli.py`, `unvibecode/archive.py`) returned 404; code search for `PUBLIC_PREVIEW_TOKEN`, `MAX_UPLOAD`, and `CustomerDashboardRenderer` returned no results. Searches for commits mentioning `0.4.0`, `v0.4.0 release`, and `packaging client 0.4.0` returned none. The installed wheel's public client code is therefore the direct source evidence for this version; I could not verify a matching source snapshot in the public repository. No private hosted-engine source was inspected.

## Module and function map

The installed package contains six Python modules:

| Module | Important functions/classes | Role and flow |
|---|---|---|
| `__init__.py` | `__version__` | Exposes version `0.4.0`. |
| `__main__.py` | imports `cli.main`, exits with its result | Enables `python -m unvibecode`. |
| `cli.py` | `main`; nested `download`, `local_text`, `render` | Parses `health`, `review`, `resume`; dry-run lists selected paths; review packs and submits; polling consumes presentation events; interim/final result downloads extract into a temp directory and copy into `--output`; final report is located and optionally opened. |
| `archive.py` | `source_files`, `pack`, `extract_safe` | Walks/filter source, creates bounded ZIP uploads, validates and extracts downloaded ZIP entries. |
| `client.py` | `NoRedirect`; `Client.__init__`, `request`, `submit`, `status`, `download`, `interim` | Builds HTTP requests, adds bearer authorization, uses a 120-second per-request timeout, maps selected HTTP/URL errors, streams downloads, and does not retry POST automatically. |
| `presentation.py` | `enable_terminal_redraw`, `CustomerDashboardRenderer`, `open_customer_report`, `open_reports_after_summary` | Enables interactive ANSI redraw, renders events, clears dashboard, and opens final HTML. The Unicode row-count defect is the separate existing candidate. |

Data flow:

```text
console entry point / python -m
  -> cli.main(argv)
     -> --dry-run: archive.source_files -> print paths, return 0
     -> review: archive.pack -> Client.submit -> job_id
     -> resume: supplied job_id
     -> Client.status(job, cursor) -> presentation event rendering
     -> Client.interim/download -> temporary ZIP -> archive.extract_safe
        -> copy extracted first-level items into --output
     -> locate *-unvibecode-full.html -> final summary/browser
```

Configuration comes from `UNVIBECODE_API_URL` or the default API URL in `client.py`; the public preview token is a package constant. The API URL rejects credentials, query strings and fragments, requires HTTPS except loopback HTTP, and disables redirects. The client uses urllib and `ProxyHandler({})`. It maps HTTP 401/404/409/413/422 specially and wraps other HTTP errors and URL errors as `RuntimeError`. There is no automatic retry. Upload archive creation and downloaded result extraction use `TemporaryDirectory`; output copies persist under the requested output directory. CLI catches `OSError`, `ValueError`, and `RuntimeError`, plus `KeyboardInterrupt`; unexpected exception types can escape.

Source line map for the reproduced path:

- `client.py:25–49` — HTTP request, destination streaming, response parsing and caught `HTTPError`/`URLError`.
- `client.py:58–62` — final/interim download endpoint wrappers.
- `archive.py:55–94` — `extract_safe`; `zipfile.ZipFile(archive_path)` is opened at line 59.
- `cli.py:45–58` — nested `download()` writes the response to a temporary ZIP and calls `extract_safe()` at line 50.
- `cli.py:107–111` — after a completed job, final download is called.
- `cli.py:118–126` — the outer handler catches only `OSError`, `ValueError`, `RuntimeError`, and `KeyboardInterrupt`; `zipfile.BadZipFile` is not among the listed types.
- `cli.py:118–122` — the recoverable error branch prints `To recover this review: unvibecode resume {job}` only when an exception reaches the handled error branch.

The release metadata README says: “On an interruption or recoverable connection error, use the displayed resume command rather than starting another analysis request.” The reproduced early-EOF transfer takes a different path: urllib returns after the short body, then ZIP parsing raises `BadZipFile`, bypassing that recovery message.

## Areas investigated

- **Archive and selection:** reviewed extension and filename filters, path-relative naming, size/count limits, empty archive behavior, archive writing and safe extraction. Existing junction traversal and #632 credential filename exclusion were excluded. The public README explicitly says source selection uses an extension allowlist and filename exclusions rather than full `.gitignore` semantics; that expected limitation was not treated as a defect.
- **Paths and temporary files:** reviewed symlink and path checks, reserved Windows names, duplicate member checks, output temp directories, and first-level copy behavior. The junction candidate was not repeated.
- **API/network:** reviewed URL validation, headers, redirects, timeouts, error mapping, retry behavior, JSON parsing and download streaming. Mocked the full CLI flow against fake and loopback-only services; no external API was contacted.
- **Response processing/output:** tested completed-job ZIP handling for a valid archive, invalid bytes, and an early-EOF response with a larger declared `Content-Length`.
- **CLI/configuration:** reviewed `health`, `review`, `resume`, dry-run, `--output`, `UNVIBECODE_API_URL`, exit paths, and browser-opening conditions.
- **Dependencies/platform:** metadata declares Python >=3.11. The tests ran on Windows/Python 3.15.2. No package changes or installs were made.

## Confirmed candidate: unhandled invalid/truncated result ZIP

### What is wrong

After the service reports `completed`, the CLI downloads a ZIP and passes it to `extract_safe()`. If the response body is invalid or ends early, `zipfile.ZipFile` raises `zipfile.BadZipFile`. `cli.main()` does not catch this exception type. The command therefore terminates with a traceback rather than its handled `[STOPPED]` message and resume command.

### Root cause

The client writes response chunks to the destination and does not verify the downloaded byte count against `Content-Length` or otherwise validate that the ZIP is complete before returning. The extraction layer correctly refuses invalid ZIP bytes, but `BadZipFile` is outside the CLI's exception tuple. Thus a short successful HTTP response reaches ZIP parsing and escapes the CLI's error handling.

This establishes the client-side exception behavior only. The test does not establish that the hosted service produces bad archives, nor any backend root cause.

### Expected versus actual

- **Expected:** a malformed/interrupted result download is reported through the CLI error path, with the known job's resume command, in line with the documented recovery guidance.
- **Actual:** an uncaught `zipfile.BadZipFile` traceback, process exit code 1, no `[STOPPED]` message, and no resume command. The incomplete final ZIP is not extracted into the output folder.

### Reproduction tests and exact commands

No real service was contacted. Both harnesses use isolated temporary repositories containing only `ordinary.py`.

1. Invalid bytes through a fake completed-job client, three independent runs plus a valid archive control:

   ```powershell
   python .\new-bug-investigation\malformed_result_probe.py
   ```

   Evidence: `malformed_result_probe.py`, `malformed-result-probe.log`. Each invalid archive run exited 1 with `zipfile.BadZipFile: File is not a zip file`. The valid ZIP control exited 0 and printed `COMPLETE`. The harness itself exited 0 because it verified those expected observations.

2. Actual installed `Client` and CLI against a local loopback HTTP server, three early-EOF result responses plus a valid download control:

   ```powershell
   python .\new-bug-investigation\truncated_download_probe.py
   ```

   Evidence: `truncated_download_probe.py`, `truncated-download-followup.log`. The mock returned HTTP 200 with a short body but a larger `Content-Length`, then closed the response. Each of three runs exited 1 with uncaught `BadZipFile`; the valid download control exited 0. The harness exited 0 after validating the results. It contacted only `127.0.0.1`; no upload or hosted request occurred.

   An initial diagnostic log, `truncated-download-probe.log`, specifically checked for `IncompleteRead` and found none. That check exited 1 because the actual repeated exception was `BadZipFile`; the follow-up log records the correctly classified result. This is one candidate/failure path, not a second finding.

### Developer impact

A developer can lose access to results from a completed job when result transfer ends early or the downloaded ZIP is malformed. The CLI exits with a traceback instead of showing its documented recovery instruction. Because job IDs are the references used to resume and the CLI does not print the ID in this exception path, recovery is materially harder. The test proves this local-client behavior under a controlled invalid response; it does not measure how often such responses occur in production.

## Rejected or not accepted hypotheses

- **IncompleteRead as a separate bug:** rejected as a separate candidate. The controlled early-EOF server response did not raise `IncompleteRead`; it produced the same unhandled `BadZipFile` path as malformed bytes.
- **Archive size-check/file-mutation race:** not accepted. It would overlap limit-validation territory (#639/#654) and was not demonstrated as an independent, high-impact failure.
- **Output folder conflict leaving partial output:** not accepted. The code can copy earlier items before encountering a later conflict, but no controlled test established misleading user impact or a documented atomicity guarantee.
- **Path normalization / reserved names:** inspected but no independently reproduced failure was established. No claim is made.

## Duplicate investigation

Read-only public GitHub searches were performed against `FinanceFlash/unvibecode` issues and pull requests using `BadZipFile`, `truncated result download`, `corrupt results ZIP`, `malformed results archive`, `resume download connection interrupted`, and `download archive incomplete`.

- `BadZipFile`: no issue or PR result.
- `resume download connection interrupted`: no issue or PR result.
- The other searches returned keyword-overlap results, not this behavior: #473 concerns unsupported notebook coverage; #365 concerns credential screening of exported context ZIPs; #632 concerns source files omitted by filename filters. None describes malformed final-result ZIP downloads escaping CLI error handling.
- PR searches returned no matching result for these queries.
- Commit searches for `BadZipFile`, `result download archive`, `extract_safe malformed zip`, `download validation`, `0.4.0`, `v0.4.0 release`, and `packaging client 0.4.0` returned no commits.

These searches did not find a report of the same client failure. They cannot prove global originality or exclude an unindexed/differently worded report. Known issues #544/#557, #632, #639/#654, #642, #652, #649, and #365 were not accepted as this candidate.

## Comparative ranking

Scores are evidence-based estimates against the requested rubric, not measured product metrics. Existing findings are included for comparison only.

| Candidate | Technical depth /35 | Reproducibility /30 | Developer impact /20 | Originality /10 | Clarity /5 | Total /100 |
|---|---:|---:|---:|---:|---:|---:|
| New: invalid/early-EOF result ZIP escapes CLI handler | 20 | 30 | 13 | 8 | 5 | **76** |
| Existing: Windows external NTFS junction files enter local archive | 27 | 30 | 18 | 4 | 5 | **84** |
| Existing: full-width Unicode undercount leaves stale dashboard rows | 22 | 30 | 9 | 5 | 5 | **71** |

The new result-download candidate may be stronger than the Unicode finding because it blocks delivery of results and bypasses the documented recovery instruction, rather than leaving stale presentation text. It does not clearly beat the junction finding, whose impact can include packaging files outside the selected repository. The new candidate also depends on an invalid or prematurely closed successful response, so frequency is unmeasured.

## Final classifications and limitations

- **Confirmed client behavior:** malformed/early-EOF final ZIP causes uncaught `BadZipFile`, exit 1; reproduced three times for each test form with a valid ZIP control.
- **Reproduced but conditional:** result integrity and CLI recovery failure under invalid HTTP 200 response bytes.
- **Not established:** any hosted service defect, production frequency, private backend cause, or broader data loss.
- **Originality:** searches found no close duplicate, but absolute originality cannot be guaranteed.
- **Public-source limitation:** installed client source was directly inspected; a matching 0.4.0 source snapshot could not be located in the public repository default branch/search index.

## Exact next steps before any Track 1 issue draft

1. Confirm the challenge permits a mocked/local malformed response as a qualifying client-only reproduction.
2. If preparing a draft, describe only the public-client handling bug: `BadZipFile` escapes `cli.main()` after an invalid/truncated result download; do not attribute it to the hosted service.
3. Include the two test logs and valid-ZIP control, and state that the malformed response was served by an isolated local mock.
4. Recheck the public issue/PR tracker immediately before submission and compare any newly found report by failure mechanism.
5. Do not claim production frequency or server-side root cause without additional evidence.
