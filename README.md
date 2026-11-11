# UnvibeCode Engineering Challenge 2026 — Track 1

This repository preserves the investigation artifacts for Candidate 3, a reproduced client-side result-download failure in UnvibeCode 0.4.0.

**Official Track 1 submission:** [FinanceFlash/unvibecode issue #666 — API client accepts premature EOF before Content-Length; CLI crashes on BadZipFile](https://github.com/FinanceFlash/unvibecode/issues/666)

## Candidate 3: premature EOF during result download

The local reproduction uses a loopback HTTP mock. It returns HTTP 200 with a declared `Content-Length` of 256 bytes but sends only 11 bytes before closing the connection. In three repeated truncated-response runs, the CLI exits with an uncaught `zipfile.BadZipFile` exception. A valid-ZIP control run exits successfully.

The test did not contact the hosted UnvibeCode service. It demonstrates the client-side behavior for the tested response shape; it does not establish production frequency or prove that the hosted service routinely sends truncated responses.

## Files in this repository

| File | Purpose |
|---|---|
| [Candidate3-API-Premature-EOF-Bug-Report.md](./Candidate3-API-Premature-EOF-Bug-Report.md) | Focused, nine-section report matching the official Issue #666 submission. |
| [final-new-bug-discovery-report.md](./final-new-bug-discovery-report.md) | Broader investigation and candidate-selection report, including source-provenance limits and comparison context. |
| [truncated_download_probe.py](./truncated_download_probe.py) | Python reproduction probe using a local loopback mock HTTP server and the installed UnvibeCode CLI flow. |
| [truncated-download-followup.log](./truncated-download-followup.log) | Fresh Windows output showing the three truncated-response failures and the successful valid-ZIP control. |

## Test environment

- UnvibeCode: 0.4.0
- Operating system: Windows 10, build 19045
- Python: 3.15.2
- Network: local loopback mock HTTP server only; no external API requests during the reproduction
- Mock response: 256 bytes declared, 11 bytes received, 245-byte shortfall

## Evidence boundaries

- The reproduction confirms the observed failure in the installed 0.4.0 client/CLI flow for the mocked premature-EOF response.
- A matching historical 0.4.0 source snapshot was not found in the public repository. Source line references in the report refer to the installed package inspected during testing.
- The evidence does not establish how often this response occurs in production, whether the hosted service emits it, or whether a job result is permanently lost.
- The suggested fixes are defensive recommendations; maintainers should confirm the exact implementation root cause against the released source.

## Official submission

The challenge submission is the GitHub issue linked above. This repository is a supporting archive of the report and local reproduction evidence; it is not a second issue or a pull request.
