# Partner-selection abnormal exit: first report

Status: reproduced and corrected for the tested transition. The user reported an exit near partner selection while holding Tab. A subsequent headless replay reproduced it without Tab input; this was not a paced windowed A/B test of turbo.

## Reproduction and correction

The diagnostic replay reached the same null PC with RA `0x8008312C` and SP `0x1F8003CC`, at frame 36,388. The newly enabled function trace identified `0x80083118` as the last native entry. Live RAM contained a different routine there from the compiled static-overlay implementation. The generated dispatcher validated range `0x83054..0x831E7` against CRC `0x4F8C65D8`, but the halted RAM's CRC was `0x9F669CC2`. The cached validator had accepted code that no longer matched.

The stale implementation read a call target from its expected stack layout and transferred to zero. This explains the matching terminal state in both runs. Identifying the precise missed write/invalidation path remains useful upstream work; the correction does not depend on guessing that path.

Shinka redirects generated static-overlay validation calls to `src/overlay_guard.c`. It computes CRC from current RAM on every call, bounds-checks all ranges, and rejects changed code so dispatch falls back to the interpreter. Upstream source and generated game code remain unchanged. Full CRC validation adds work per dispatch; cache optimization must wait for a verified invalidation contract.

Validation:

- The native regression test accepts known matching code, rejects a changed byte without any generation notification, accepts restored bytes, handles split ranges, and rejects invalid ranges/null memory.
- Release runtime and test executable build; CTest regression and all three disc-tool tests pass.
- Reloading the same pre-transition checkpoint reaches registration instead of exiting.
- Name entry, Balanced Pack selection, account confirmation, and the 100% registered screen render and accept input.
- Local SCPH-1001 checkpoints in `output/partner-repro-saves`: slot 4 title, slot 7 before the failing transition, slot 9 starter-pack selection. These are not distributed.

This corrects the reproduced stale-overlay exit. Exploration, battles, in-game card saving, sustained performance, and windowed fast-forward still require validation.

## Original failure evidence

The visible-host log ends with `execution completed, PC=0x00000000`. The runtime's corresponding path identifies this as an abnormal return from top-level guest dispatch. This is evidence of a guest control-flow exit, not evidence of a Windows access violation. Do not attribute it to controller support or turbo alone without a paired reproduction.

Preserved locally under ignored `output/crashes/partner-selection-20260909/`: visible-host log, exit trace, last-run report, final heartbeat, and available freeze dumps. Raw artifacts contain game memory and are not tracked.

Most reliable terminal state comes from the final heartbeat and explicit exit trace:

- Frame 13,191; PC `0x00000000`; RA `0x8008312C`; SP `0x1F8003CC`.
- Last recorded store `0x80025168`, in a byte-copy loop. A last-store address alone does not identify the cause.
- No unsupported-interpreter opcode or unknown-dispatch entries were reported.
- Explicit exit trace has zero recorded function entries, so it cannot identify the transfer that published zero.
- The last-run report's CPU fields disagree with the explicit trace/heartbeat and include apparent host-address fragments. Treat those late CPU fields as unreliable until report lifetime is investigated.
- Available automatic freeze dumps are from early boot (frames 407/423), not from partner selection. No player-run savestate was found.

Next reproduction should save immediately before partner selection, then compare the same transition with Tab released and held. If it fails, retain live guest state with the launcher's `-HoldOnGuestExit` switch. This uses the pinned runtime's `PSX_EXIT_HALT` diagnostic path, which keeps the debug server available after this specific null-PC exit instead of immediately shutting down. It is not a fix or a general Windows-crash handler.

Then inspect the transition caller, loaded overlay bytes, and the transfer producing PC zero. Compare static-overlay and fallback execution if the same checkpoint reproduces the failure. Do not redirect PC or bypass the selection logic merely to keep the window open.
