# UnvibeCode Engineering Challenge 2026 — Track 1

This repository contains the focused report and local reproduction evidence for a client-side result-download failure observed with the installed UnvibeCode 0.4.0 package.

**Official Track 1 issue:** [FinanceFlash/unvibecode issue #666 — API client accepts premature EOF before Content-Length; CLI crashes on BadZipFile](https://github.com/FinanceFlash/unvibecode/issues/666)

## Finding

The client can return a result-download body even when the HTTP response ends before its declared `Content-Length`. The CLI then passes the incomplete body to ZIP extraction. In the reproduced path, `zipfile.BadZipFile` escapes the CLI's normal error handler and terminates the process with exit code 1.

## Reproduction

The local probe uses a loopback HTTP mock. It returns HTTP 200 with a declared `Content-Length` of 256 bytes but sends only 11 bytes before closing the connection. Three truncated-response runs exit with an uncaught `zipfile.BadZipFile` exception. A valid-ZIP control run exits successfully.

The mock reproduction did not contact the hosted UnvibeCode service. It demonstrates the client-side behavior for the tested response shape; it does not establish production frequency or prove that the hosted service routinely sends truncated responses.

## Challenge repository trial

The public repository used for the separate challenge client trial was [pallets/flask](https://github.com/pallets/flask), at commit `49943b5a94413a530761350f04e896f76e8d620e`. A local `--dry-run` completed successfully and listed 140 files. This repository trial is distinct from the loopback reproduction of the result-download failure; the hosted analysis did not complete because the service returned an API quota error.

## Files

| File | Purpose |
|---|---|
| [API-Premature-EOF-Bug-Report.md](./API-Premature-EOF-Bug-Report.md) | Focused report matching the official Issue #666 submission. |
| [truncated_download_probe.py](./truncated_download_probe.py) | Python reproduction probe using a local loopback mock HTTP server and the installed UnvibeCode CLI flow. |
| [truncated-download-followup.log](./truncated-download-followup.log) | Windows output showing the three truncated-response failures and the successful valid-ZIP control. |

## Test environment

- UnvibeCode: 0.4.0
- Operating system: Windows 10, build 19045
- Python: 3.15.2
- Network during reproduction: local loopback mock server only
- Mock response: 256 bytes declared, 11 bytes received, 245-byte shortfall

## Evidence boundaries

- The reproduction confirms the observed failure in the installed 0.4.0 client/CLI flow for the mocked premature-EOF response.
- A matching historical 0.4.0 source snapshot was not found in the public repository. Source line references in the report refer to the installed package inspected during testing.
- The evidence does not establish how often this response occurs in production, whether the hosted service emits it, or whether a job result is permanently lost.
- The suggested fixes are defensive recommendations; maintainers should confirm the exact implementation root cause against the released source.

## Official submission

The official Track 1 submission is the GitHub issue linked above. This repository is a supporting archive of the report and local reproduction evidence; it is not a second issue or a pull request.
