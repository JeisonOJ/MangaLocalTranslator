# MangaLocalTranslator Capture — E3.1 / 0.3.1

Standalone Edge Manifest V3 image downloader. The user selects the image and independently chooses ArrowRight, ArrowLeft or Selected Click Control. The extension trusts those choices: it does not inspect chapter identity, titles, tooltips, CSS classes or URL patterns to decide whether the control is appropriate. Manga title and chapter are entered manually for file organization only.

## Load/update and use

1. Stop capture. Open `edge://extensions`, enable Developer mode, and Load unpacked: `C:\Dev\Codex\MangaLocalTranslator\extension`. For an existing installation click Reload.
2. **Refresh the reader tab after extension reload.** Select the image again. Select a control only for Click mode; arrows require no click selection.
3. Enter title, chapter, maximum pages and timeout. Select Image, grant the reader-origin permission, and click the actual loaded manga image. Escape cancels; reopen the popup afterward.
4. Choose ArrowRight, ArrowLeft or Selected Click Control. For Click mode, Select next-page control and click the actual button, link or clickable area. That selection click is intercepted and does not navigate. For an area where click position matters, pick the intended point (for example, its right-hand side). The relative point is retained. Labels are displayed for convenience but never used to approve/reject or match the control.
5. Test Download saves 0001 and stops. Inspect the image. Start reuses that completed download and performs only the chosen navigation action; the next saved page is 0002. Start without Test begins at 0001. Closing/reopening the popup does not reset state.
6. Stop keeps completed files and prevents further navigation. An already dispatched browser download may finish. Maximum pages and bounded timeout also stop capture. Keep the reader tab open; avoid manually navigating during a run.

Downloads: `Mangas/<sanitized title>/Capítulo <sanitized chapter>/0001.jpg`. Names are sanitized; Edge uniquifies conflicts and never overwrites files. Different raw titles/chapters sanitizing to an already owned folder are rejected. A changed title, chapter or selected resource requires a fresh image selection. A used/stopped context cannot silently restart: reselect explicitly. A fresh run in a previously used folder starts at 0001 with conflict suffixes; use a distinct chapter label for clean repeated experiments.

## The loop

Download the selected image resource → confirm browser download completion → send the chosen arrow or click the selected control once → wait for a stable new resource → download → repeat. The three methods are independent: arrows neither require nor use a saved click control. No guessed URLs, automatic method fallback, chapter crawling or retry loop. Same-origin pathname changes are permitted without any chapter metadata. Cross-origin navigation stops capture. Manual Stop, maximum count, duplicate identity, missing/ambiguous selection, download failure and bounded timeout remain.

currentSrc is preferred over src. Files use original resource bytes/resolution rather than screenshots or displayed size. No hidden URL inference, transcoding or upscaling. Typed jpg/jpeg/png/webp/gif/avif/bmp URLs are supported; unknown-extension, blob/data URLs, frame/canvas-only readers are unsupported. Non-image responses stop and remain available for inspection.

## Structural reacquisition

Descriptors record the selected element's tag, ancestor path, child slot and sibling tag structure. Identical attributes on multiple buttons no longer force a label/class-based guess. A still-connected **visible** user-selected node can be retained. Detached/hidden nodes are not blindly reused. Across a replaced document, matching structural position reacquires the intended control; a unique stable ID with the same ancestor tag chain is a fallback if its position moved. Missing/changed ambiguous structures stop. A site reordering otherwise indistinguishable controls can defeat positional identity; no generic algorithm can prove semantic equivalence in that case. Reselect after substantial reader layout changes.

Images first use structural matching. A unique compatible image descriptor (ancestors/classes/alt/aspect) remains a fallback when the layout replaces or appends images; hidden old image nodes are excluded. No chapter discovery is involved. Image observation requires one second of stable resource/dimensions/fingerprint before download. Slow placeholders and responsive image swaps still require manual validation.

The selected relative click point is replayed in the reacquired element's current rectangle using a synthetic DOM click. It is **not trusted input** and does not bypass trusted-event restrictions. Sites requiring pointer gestures, trusted clicks or nonstandard input may not advance. If the chosen control opens a new tab, capture does not transfer to it. The extension does not reject labels such as Next chapter: it follows the explicitly selected control, so use maximum count / Stop to control the intended chapter extent. No chapter-end success is inferred from a timeout.

## Navigation selection management

The popup displays the active method and persists the selected method across closing/reopening. Arrow modes leave a saved click selection available but do not inspect or use it. Switching back to Click can reuse it if it remains valid. A missing/unresolvable Click selection produces a clear error before capture starts, rather than trying an arbitrary control.

**Clear Navigation Selection** removes only the saved control and its live reference. It preserves the selected image, form values, completed count and downloaded files. During an active Click capture it stops further capture with `control_cleared`. During an arrow capture it does not stop the run. Changing methods during capture changes the next action without repeating/cancelling an action already dispatched. If switching to Click cannot resolve a saved control, capture stops with a clear message; it never silently falls back to arrows.

## E3 regression: reproduced and fixed

E3 compared descriptors and nested structural path objects with `JSON.stringify`. That compared object property insertion order, not semantic field equality. Its click handler discarded the live user-selected node whenever the stored/message descriptor had reordered keys. Its structural matcher then rejected the same path for the same reason; multiple buttons led to `control_ambiguous` before the first click. Image watch restoration used the same faulty comparison.

Two new tests reproduced these failures on the unpatched E3 code: reordered stored keys plus a still-valid selected button, and reordered nested path keys across documents with identical buttons. Both failed before the fix and pass afterward. Comparisons now check explicit field values, independent of property order. The live selection is retained when valid, even after sibling layout changes; structural reacquisition occurs only when the live element is unavailable. The picker overlay was also included in the saved sibling-family path, then removed when selection ended. Path construction now excludes that extension-owned overlay, so a clean destination document can match it. A dedicated regression test covers this; no new title/class/chapter validation was added. The agent did not inspect the original failing browser session's runtime objects, so this establishes a concrete reproduced regression rather than a claim that every live-site failure has the same cause.

## Concise diagnostics

Popup status and persisted `session.navigation` / `session.observation` distinguish:

- `control_missing`, `control_ambiguous`, `control_unavailable`, `selection_outdated`: no click dispatched because the selected target cannot be recovered safely.
- `arrow_dispatched`: the chosen arrow keydown/keyup pair was dispatched; no click control was used. `arrow_dispatch_failed` / `navigation_failed` records a dispatch error.
- `click_failed`: invoking the click threw an exception.
- `click_dispatched`: the click event was observed at the selected target. This does not prove the reader accepted it. `match` records retained selection, structural path or unique-ID/ancestor recovery; relative point and defaultPrevented are recorded too. defaultPrevented can mean normal JavaScript navigation, not failure.
- `click_unconfirmed`: dispatch returned but the extension's click observer did not receive it.
- `click_ack_unavailable`: the reply channel failed, possibly because the document navigated. No second click is issued; the bounded image wait continues.
- `image_missing`, `image_loading`, `image_settling`, `image_ready`: whether a visible selected-equivalent node and loaded resource were observed.
- Timeout text includes click status, image status, and whether a changed resource was observed but remained unready. A missing image differs from a dispatched click with an unchanged image. A watchdog firing without DOM observations says so.

E2 code review found three plausible failure contributors: connected-but-hidden image nodes could pin observation to the previous page; labels/classes did not distinguish structurally identical controls; and click success was replied **before** invocation. Also `.click()` did not retain a user-selected point in a clickable area. These are corrected/tested offline. The user's original two-image timeout alone does **not** establish its exact live-site cause. A live rerun is needed, using the new diagnostic if it stops again. No reader-specific workaround or trusted-event bypass was added.

## Persistent state / privacy

Local extension storage retains settings, image/control descriptors, job state, download IDs and previous session metadata. Messages, tab/download events and a 30-second fallback alarm revive a dormant worker; deadlines are persisted. No long-running popup is required. Browser restart stops rather than automatically resumes. Download intent is saved before dispatch; ambiguous interrupted dispatch stops instead of risking another download. Known IDs reconcile with Edge. Completion deadline is 120 seconds; late downloads may still finish in Edge.

Duplicate resource URLs (excluding fragments) stop capture. Canvas sample fingerprints additionally detect identical content at different URLs when pixel access is permitted; CORS taint falls back to URL identity without extra requests. Duplicate checks apply per capture session, not across fresh jobs. Different signed/re-encoded resources may evade identity checks; identical URL reuse is conservatively rejected even if its bytes change.

Permissions remain activeTab, scripting, storage, downloads and alarms, with runtime permission for the selected HTTP(S) reader origin. No Python integration, local server, Native Messaging, registry modifications, remote APIs, telemetry or dependencies. No guessed next-chapter URLs. Origin checks still stop unexpected cross-origin navigation; the tab itself may already have navigated, but capture does not continue there. URLs and labels can contain tokens and stay in local storage; clear extension data when desired.

## Validation

No install step:

```powershell
Set-Location C:\Dev\Codex\MangaLocalTranslator\extension
npm test
npm run check
```

Offline tests mock browser APIs/DOM and cover changing pathnames/resources, fresh-document image/control recovery, hidden retained image nodes, identical control attributes, missing/ambiguous controls, chosen click position, click failures/acknowledgement, Test → Start, Start without Test, duplicates, Stop, limits, download failures, timeouts, cross-origin blocking and ambiguous dispatch recovery. They do not establish actual Edge or reader compatibility.

Manual E3.1 regression checklist:

1. Reload extension, refresh reader, select the image. Use a new folder label, maximum 4, timeout 15 seconds. Choose ArrowRight with no click control and test capture. Repeat in a fresh context with ArrowLeft; only the configured arrow should be dispatched.
2. Test Download, inspect 0001 and original resolution, close/reopen popup, Start. Confirm no duplicate 0001.
3. In a fresh stopped context choose Click, select the intended button among identical-looking controls, then Test → Start. Confirm the first click uses the selection and later full-document/path changes reacquire the same intended position. Capture at least 0002 and 0003 and compare with the reader.
4. Change Click → ArrowRight/ArrowLeft while waiting: no repeat action, and the next action uses only the chosen arrow. Close/reopen the popup and confirm its method persists. Switch back to Click and confirm the saved target can be reused.
5. If the reader stops, record the complete status including click and image diagnostics. Do not assume a timeout means end of chapter or that a dispatched event means successful reader navigation.
6. Test missing/duplicated controls, a blocked download, a repeated page and a cross-origin destination. Expect safe stops, no retries or overwrites. Preserve completed files.
7. Clear Navigation Selection: image, title, chapter and downloaded count must remain. Arrows still work. Click without a target must show a clear error. During active Click capture clearing stops further capture. Stop and maximum 1 must prevent further navigation in all modes.
8. Test worker suspension mid-wait/mid-download: known IDs should recover or an ambiguous dispatch should stop without duplication. Restart Edge: capture remains stopped.

No E3.1 live reader test has been performed by the agent. Offline validation: 31 tests passed, including key-order regressions, independent arrows, mode switching, clearing and popup persistence; all JavaScript syntax checks passed. Existing translation experiments were untouched. No commits or pushes.

## E4A performance diagnostics (measurement only)

Open the optional Performance section in the popup. Copy Performance Report copies plain text via the user-initiated clipboard API; if browser policy denies clipboard access, an error is shown and the displayed text remains selectable. No permission was added. Reports omit names, URLs, credentials, filenames and raw error details.

Download time runs from calling the downloads API until this extension confirms completion via its download record. Dispatch time includes locating/matching and dispatching the action through browser messaging/scripting, separate from the following wait. It does not imply the reader accepted the event. Next-image wait ends when the existing stable-resource check accepts a new eligible image; it includes loading, DOM polling, stabilization and message delivery. Existing stabilization is at least 1000 ms with 700 ms observation polling, not a new delay. Its exact per-page contribution cannot be isolated here and is not invented.

Monotonic marks are qualified by worker lifetime. Measurements spanning a worker interruption are unavailable, never substituted with zero or wall-clock estimates. Completed stored measurements survive popup reopening and worker replacement. Total duration is a snapshot at the latest state update, includes the Test-to-Start pause for that same session, and freezes at terminal stopping. It is not a continuously ticking popup clock. A restarted worker makes an interrupted total unavailable. Paused Test duration is updated when capture resumes. Per-page rows associate each downloaded page with the preceding navigation and image wait; page 0001 has no preceding navigation. Retained history is limited to 100 completed pages; averages use only available retained samples. Average elapsed per completed page uses the full completed count and session total when available. Unfinished/failed operations have no fabricated completed-page row.

Comparison procedure: reload extension, refresh reader, choose a fresh context/folder label. Use the same maximum (for example 10) and timeout on each reader. Test Download then promptly Start, or use direct Start consistently on both. For the heavy reader choose Click and select its control; for the light reader choose ArrowRight. Allow the configured limit to stop capture, open Performance, and copy each report to separate local notes labelled by reader. Compare download, dispatch and next-image wait separately; record any unavailable samples or time spent paused after Test. Do not infer network transfer speed or optimization gains from these elapsed measurements. No capture delays, sequencing, timeout policy, permissions or navigation safeguards were intentionally changed.

## E4B detection latency update

This section supersedes earlier descriptions of the blanket 1000 ms readiness gate. Download, dispatch and next-image wait definitions, timing marks and report privacy are unchanged. The old detector discovered a changed image on a 700 ms tick and needed two further ticks to exceed 1000 ms, imposing approximately 1.4–2.1 s of detector latency even for an instantly loaded image.

The detector now responds to DOM insertion/replacement, src/srcset/sizes/style/visibility changes, captured image load/error events and watch restoration. Checks are coalesced; events arriving during a pending worker message request another check afterward rather than waiting for polling. Only the previously selected/reacquired image is evaluated. A loaded image must decode successfully, survive two requestAnimationFrame boundaries, and still have the same element identity, resource, dimensions, available pixel fingerprint and source attributes. Superseded asynchronous decode/frame results are discarded. Missing, incomplete or decode-rejected resources are not eligible. Existing background URL/fingerprint duplicate checks still reject the old page or a previously captured image. Both arrows and Click share this detector; no navigation/download code was changed for E4B.

Polling remains at 700 ms for events the browser/site does not expose. A hidden document or unavailable animation-frame API retains >=1000 ms stabilization; successful decode is still required when supported. Unsupported decode uses the existing legacy stabilization. There is no new millisecond sleep on the foreground decoded-image path. Two rendering frames are a rendering/readiness consistency check, not proof of the site's semantic final page. A fully decoded, full-size placeholder that remains through both frames cannot be distinguished generically from a real manga page; the old one-second delay could not guarantee that either. Watch the first run for lazy-loading/responsive intermediates. Background throttling, decode speed and actual resource loading can still dominate wait time.

Manual comparison: reload extension, refresh each reader, start a fresh context with the same maximum 10 and timeout used for E4A. Use Selected Click Control on the heavy JPG reader and ArrowRight on the lightweight WebP reader. Use the same Test → Start procedure and pause duration as before. Inspect every downloaded image for correct order, duplicates, placeholders, completeness and original resolution; check the maximum stops at 10. Copy Performance Report from each completed session and compare the next-image-wait column independently from download/dispatch. Repeat with a slow load and with a last-page/no-op navigation to confirm waits and timeouts still behave correctly. No real-world speed improvement is claimed until these browser tests are repeated.

## E5 download folders: verified request path, browser destination still needs manual verification

The folder builder was already implemented and remains unchanged. Both Test and Start use the same `chrome.downloads.download` call with a relative filename, for example `Mangas/Nue no Onmyouji/Capítulo 01/0001.jpg`. Chapter input is a string, preserving leading zeros. Original extensions and sequential numbering remain intact. The current source contains no fallback that flattens this path into Downloads. Offline tests now assert exact JPG/WebP paths at the API boundary for Test → Start and direct Start, including sanitization and chapter 01.

E5 records the requested relative path with each completed page and shows it alongside Edge's reported filename in the popup. This is diagnostic only: it does not change completion, retry, destination or navigation behavior. Absolute paths reported by Edge are displayed locally, never used as output instructions or included in Performance Report. Older records may lack the requested path.

The reported flattening's live-browser root cause is not established. Reload this unpacked extension from the intended project directory, refresh the reader, then use title Nue no Onmyouji and chapter 01 for a fresh selected context. Test Download, then Start to produce 0002. Compare popup requested/reported paths and use Edge Downloads → Show in folder; the downloads list's basename alone does not establish the containing folder. Check edge://settings/downloads for the configured root location. That root determines where Mangas begins; changing the root alone should not remove requested subfolders. If a save chooser appears, inspect its selected destination rather than assuming it kept the requested folder.

If the requested path is correct but Edge reports a root-level file, repeat with other download-organizer/manager extensions temporarily disabled and without external download interception, then restore them. Chromium permits other extensions' onDeterminingFilename listeners to override a requested filename; do not add a competing listener here. Also check for a stale/duplicate unpacked installation or a different extension directory. These are possible explanations, not verified causes on this PC. See official API documentation: https://developer.chrome.com/docs/extensions/reference/api/downloads (DownloadOptions.filename and onDeterminingFilename).

No promise of actual Edge folder creation is made until this manual test passes. No detection, loader filtering, duplicate protection, navigation, download confirmation, permissions or dependencies changed for E5.
