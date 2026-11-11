# Candidate 3 — API client accepts premature EOF before Content-Length; CLI crashes on BadZipFile

## 1. Problem summary

The UnvibeCode 0.4.0 API client can return a result-download body even when the HTTP response ends before the declared `Content-Length`. The CLI then passes the incomplete body to ZIP extraction. In the reproduced path, `zipfile.BadZipFile` escapes the CLI's normal error handler and terminates the process with exit code 1.

This report concerns client-side handling of an incomplete result download. It does not establish that the hosted service routinely sends truncated responses.

## 2. Test environment

- UnvibeCode: 0.4.0
- OS: Windows 10, build 19045
- Python: 3.15.2
- Transport: local loopback mock HTTP server only
- External service/API: not contacted during the reproduction
- Reproduction used the installed UnvibeCode client/CLI flow.

## 3. Steps to reproduce

1. Run the local reproduction probe against the installed UnvibeCode 0.4.0 package.
2. The probe starts a loopback HTTP mock and drives the client/CLI upload, status, and result-download sequence.
3. For the truncated-response case, the mock returns HTTP 200 and declares `Content-Length: 256`.
4. The mock sends only 11 bytes (`b"PK\x03\x04partial"`) and then closes the sending side.
5. Repeat the truncated case three times.
6. Run the valid-ZIP control case using the same local flow.

Observed response sizes:
- Declared length: 256 bytes
- Actual body: 11 bytes
- Shortfall: 245 bytes

## 4. Expected behavior

The client should not treat a response that ends before its declared length as a complete result download. It should reject the incomplete response before ZIP extraction and report a controlled download/integrity error.

The CLI should handle an invalid or incomplete result archive without an uncaught traceback. Where the job ID is still available, the error path should retain or display the documented recovery guidance. A valid result ZIP should continue to complete normally.

## 5. Actual behavior

The fresh Windows run produced:

```text
MOCK_CONTENT_LENGTH=256
MOCK_BODY_LENGTH=11
MOCK_CONTENT_LENGTH_SHORTFALL=245

CASE 1 mode=truncated OS_EXIT_CODE=1
zipfile.BadZipFile: File is not a zip file

CASE 2 mode=truncated OS_EXIT_CODE=1
zipfile.BadZipFile: File is not a zip file

CASE 3 mode=truncated OS_EXIT_CODE=1
zipfile.BadZipFile: File is not a zip file

CASE 4 mode=valid OS_EXIT_CODE=0
STDERR:
<empty>

TRUNCATED_RESPONSE_REPEATED_UNHANDLED_BADZIPFILE=True
VALID_DOWNLOAD_CONTROL_EXIT_ZERO=True
```

All three truncated cases ended in an uncaught `BadZipFile`. The valid ZIP control exited successfully. The exception bypasses the CLI's normal handled-error path, so its normal recovery message is not printed.

## 6. Evidence

The reproduction is based on a locally generated loopback mock response and the installed client/CLI, not on a copied report or reproduction from an existing issue.

Fresh local log:
`new-bug-investigation/truncated-download-followup.log`

Probe:
`new-bug-investigation/truncated_download_probe.py`

Relevant installed-package source locations inspected:

- `client.py:25–49`: request handling, response streaming, and HTTP/URL error handling.
- `client.py:58–62`: final/interim download wrappers.
- `archive.py:55–94`: archive extraction; `zipfile.ZipFile(archive_path)` at line 59.
- `cli.py:45–58`: download helper writes the response to a temporary ZIP and invokes extraction.
- `cli.py:107–111`: final result download after job completion.
- `cli.py:118–126`: CLI exception handler catches `OSError`, `ValueError`, `RuntimeError`, and `KeyboardInterrupt`, but not `zipfile.BadZipFile`.

The installed 0.4.0 package was inspected locally. A matching historical 0.4.0 source snapshot was not found in the public repository, so these line references describe the installed package examined in the reproduction environment; they should not be assumed to match the current public branch.

## 7. Impact and scope

When a result download ends prematurely in this manner, the CLI can fail with an uncaught traceback instead of reporting a controlled download error. This also bypasses the normal recovery guidance in the handled-error path.

The reproduction establishes the client-side failure for the tested response shape. It does not establish how often such responses occur in production, whether the hosted service emits them, or whether any job result is permanently lost.

## 8. Suspected cause / suggested fix

The observed behavior is consistent with the download path failing to validate the received byte count against the response's declared `Content-Length` (or otherwise verify response completeness) before returning the body to the archive-extraction step.

Suggested improvements:

1. Validate response completeness before treating the download as successful. When `Content-Length` is present, compare it with the number of bytes actually received; also handle premature termination when the length is absent or transfer framing indicates an incomplete response.
2. Treat incomplete downloads as download errors and do not pass them to ZIP extraction.
3. Handle `zipfile.BadZipFile` in the CLI's controlled error path as a defensive fallback.
4. Preserve and display available job recovery information when the result download fails.

These are suggested defensive changes; the precise internal root cause should be confirmed against the maintainers' source for the released 0.4.0 package.

## 9. Duplicate check

A targeted search of the repository's issues was performed for `BadZipFile`, `Content-Length`, `premature EOF`, `truncated download`, `partial download`, `short response`, and result-archive/download terms.

The closest related report found was [#643 — API client: interrupted downloads leave partial destination files](https://github.com/FinanceFlash/unvibecode/issues/643). That report describes an interrupted read that raises a URL/network error and leaves a partial destination file. This reproduction is a different observed sequence: the mock response ends at EOF without a read exception, the client returns the short body, and the CLI subsequently fails during ZIP parsing with an uncaught `BadZipFile`.

Other reviewed issues (#644, #647, #656, and #659) concern different archive, resume, or Windows behavior and do not describe this specific premature-EOF-to-uncaught-BadZipFile sequence.

This is a bounded duplicate check, not a guarantee that no related report exists.
