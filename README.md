# UnvibeCode Engineering Challenge 2026 — Track 1

**Official Track 1 issue:** [FinanceFlash/unvibecode issue #666 — API client accepts premature EOF before Content-Length; CLI crashes on BadZipFile](https://github.com/FinanceFlash/unvibecode/issues/666)

This repository is a supporting archive for the technical finding and its local reproduction. The official competition submission is issue #666; this archive is not a second issue or a pull request.

## Challenge repository trial: Evidently

The public repository used for the Cohort 3 Track 1 repository trial was [evidentlyai/evidently](https://github.com/evidentlyai/evidently), commit `34771fe41c08ca074d96a52aaf4a45cd640cbaf5`.

Local checkout recorded for the trial:

```text
C:\Users\Dell\Downloads\Evidently_Fresh
```

Review command:

```powershell
python -m unvibecode review --repository "C:\Users\Dell\Downloads\Evidently_Fresh"
```

The run completed with PARTIAL status because the repository exceeded the supported review-size limit. The Connected Code Map and repository-context outputs were produced; the full Business Workflow and Business Risk analysis did not run. This is not represented as a complete analysis.

## Finding reported in issue #666

The UnvibeCode 0.4.0 client can return a result-download body when the HTTP response ends before its declared `Content-Length`. The CLI then passes the incomplete body to ZIP extraction, where `zipfile.BadZipFile` escapes the normal CLI error handler.

This client-side failure was verified separately using a local loopback HTTP mock. The Evidently repository trial and the loopback reproduction are separate activities; the Evidently run is not claimed to have caused the mock HTTP response or the download defect.

## Reproduction summary

The loopback mock returns HTTP 200 with a declared `Content-Length` of 256 bytes but sends only 11 bytes before closing. Three truncated-response runs terminate with an uncaught `BadZipFile`; a valid ZIP control run exits successfully.

The mock reproduction did not contact the hosted UnvibeCode service. It demonstrates the client-side behavior for the tested response shape; it does not establish production frequency or prove that the hosted service routinely sends truncated responses.

## Supporting files

| File | Purpose |
|---|---|
| [API-Premature-EOF-Bug-Report.md](./API-Premature-EOF-Bug-Report.md) | Detailed report and evidence boundaries. |
| [truncated_download_probe.py](./truncated_download_probe.py) | Loopback reproduction probe using the installed UnvibeCode CLI flow. |
| [truncated-download-followup.log](./truncated-download-followup.log) | Sanitized Windows output showing three truncated-response failures and the valid-ZIP control. |

## Test environment

- UnvibeCode: 0.4.0
- Operating system: Windows 10, build 19045
- Python: 3.15.2
- Network during reproduction: local loopback mock server only
- Mock response: 256 bytes declared, 11 bytes written by the mock, 245-byte shortfall

## Additional exploratory trial: Flask

A separate local `--dry-run` was performed against [pallets/flask](https://github.com/pallets/flask), commit `49943b5a94413a530761350f04e896f76e8d620e`; it listed 140 files. The subsequent hosted analysis did not complete because the service returned an API quota error. Flask is not the repository identified for the Evidently Track 1 trial in issue #666.

## Evidence boundaries

- The reproduction confirms the observed failure in the installed 0.4.0 client/CLI flow for the mocked premature-EOF response.
- A matching historical 0.4.0 source snapshot was not found in the public repository. Source line references in the report refer to the installed package inspected during testing.
- The evidence does not establish how often such responses occur in production, whether the hosted service emits them, or whether a job result is permanently lost.
- The suggested fixes are defensive recommendations; maintainers should confirm the exact implementation root cause against the released source.
