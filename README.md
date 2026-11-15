# UnvibeCode Engineering Challenge 2026 — Track 1

**Official Track 1 report:** [FinanceFlash/Unvibecode issue #666 — API client treats HTTP 200 response shorter than Content-Length as complete](https://github.com/FinanceFlash/unvibecode/issues/666)

This repository is a supporting evidence archive for the investigation and controlled reproduction. The official challenge report is issue #666; this repository is not a second issue or a pull request.

## 1. Real-repository investigation: Evidently

The Cohort 3 Track 1 investigation used the public [evidentlyai/evidently](https://github.com/evidentlyai/evidently) repository at commit [`34771fe41c08ca074d96a52aaf4a45cd640cbaf5`](https://github.com/evidentlyai/evidently/commit/34771fe41c08ca074d96a52aaf4a45cd640cbaf5).

The local checkout was under the Windows Downloads folder. A reproducible PowerShell command is:

```powershell
python -m unvibecode review --repository "$env:USERPROFILE\Downloads\Evidently_Fresh"
```

The exact original command line was not retained; the command above is provided as a re-run command, not as a claim about the original invocation.

The saved review page records **PARTIAL** status. The Connected Code Map and repository-context outputs were available, but the full Business Workflow & Risk Review did not run because the repository exceeded the supported review size. This archive does not represent the run as a completed business workflow or risk analysis.

## 2. Finding

The reported primary defect is in the UnvibeCode 0.4.0 API client's result-download handling: the download loop treats EOF as completion without validating the received byte count against the response's declared `Content-Length`.

In the controlled reproduction, an incomplete HTTP 200 response proceeds to ZIP extraction. The downstream `zipfile.BadZipFile` exception is not handled by the CLI's normal error boundary and terminates the process.

The Evidently investigation and the controlled HTTP reproduction are separate stages. **The mock server was not used to discover the issue.** It was created afterward to reproduce the suspected client behavior in a controlled way. The mock response was generated locally; it was not sent by Evidently, and this evidence does not establish that Evidently or the hosted UnvibeCode service caused such a response in production.

## 3. Controlled reproduction

The archived probe, `truncated_download_probe.py`, drives the installed UnvibeCode client/CLI flow against a local loopback HTTP mock. It does not contact the hosted service.

- UnvibeCode: 0.4.0
- Operating system: Windows 10, build 19045
- Python: 3.15.2
- Mock response: HTTP 200, `Content-Length: 256`, 11 bytes written by the mock
- Shortfall: 245 bytes
- Repeated truncated cases: 3; each ended in an uncaught `zipfile.BadZipFile` and exit code 1
- Valid ZIP control: 175 bytes; exit code 0

The mock-handler byte count is the number of bytes written by the test server. The archived probe does not instrument the client's `HTTPResponse.read` return count, so no direct client-read byte measurement is claimed.

## 4. Supporting files

| File | Purpose |
|---|---|
| [API-Premature-EOF-Bug-Report.md](./API-Premature-EOF-Bug-Report.md) | Detailed technical report, reproduction details, source trace, limitations, and related-issue comparison. |
| [truncated_download_probe.py](./truncated_download_probe.py) | Runnable loopback reproduction probe using the installed UnvibeCode CLI flow. |
| [truncated-download-followup.log](./truncated-download-followup.log) | Sanitized output showing three truncated-response failures and the valid-ZIP control. |

## 5. Source and evidence limitations

- The reproduction confirms the observed failure for the tested premature-EOF response shape in the installed UnvibeCode 0.4.0 client/CLI flow.
- A matching historical 0.4.0 source snapshot was not located in the public repository. Source references in the report describe the installed package inspected during testing and should not be assumed to match the current public branch.
- The evidence does not establish production frequency, prove that the hosted service routinely emits truncated responses, or show permanent loss of a job result.
- The suggested changes are defensive recommendations. Maintainers should confirm the exact implementation root cause against the released source.
- Issue #775 overlaps with the downstream `BadZipFile` symptom. Issue #666 narrows its claim to the upstream HTTP response-completeness check; the overlap is explicitly acknowledged rather than denied.

## 6. Separate exploratory trial

A separate local `--dry-run` was performed against [pallets/flask](https://github.com/pallets/flask), commit `49943b5a94413a530761350f04e896f76e8d620e`; it listed 140 files. The subsequent hosted analysis did not complete because the service returned an API quota error. This exploratory Flask run is not the Evidently Track 1 repository trial and is not the basis of the reported defect.
