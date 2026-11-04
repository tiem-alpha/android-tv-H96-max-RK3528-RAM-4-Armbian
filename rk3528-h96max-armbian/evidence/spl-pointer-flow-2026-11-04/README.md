# Compatible-pointer flow investigation

Full reasoning and source call paths:
[SPL_POINTER_FLOW_2026-11-04.md](../../docs/SPL_POINTER_FLOW_2026-11-04.md).

`experiment-summary.json` records ten verified controlled replays: eight
non-injection cases and two explicit fault injections. Individual JSON files
contain checkpoints, instruction-level value flow, all observed caller/callee
edges, memory-write regions/bounds and the exact emulator limitations.

`static-pointer-references.json` records the binary pointer locations and
driver-list layout. `preprocessor-audit.json` records source preprocessing
with the retained SPL flags and confirms exclusion of manual driver relocation.

These are software experiments, not hardware captures. The injected bad value
is supplied by the test harness; the real corrupting operation remains unknown.
No source firmware, production loader or physical storage was modified.
