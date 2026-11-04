# Hypothesis checks and handling

See [the report](../../docs/SPL_HYPOTHESIS_HANDLING_2026-11-04.md).

- Artifact/DEB/alternate-SPL records check the retained build identity chain.
- Original and hardened calloc results demonstrate the defects and correction.
- MMU result checks the corrected source with the actual table-building code.
- The three new replay JSON files distinguish corrupt initial data, a caught
  CPU write, and a normal protected-page run. Injections are explicit harness
  actions, not evidence that those actions occurred on hardware.
- The two production source patches are under `patches/patch/u-boot/legacy/`;
  patch-application results and the missing-BL31 negative test are recorded here.
- `hypothesis-diagnostic.patch` is a separate optional delta, not applied by
  the production build. Apply it after the two production patches when
  reproducing the diagnostic build.
- `diagnostic-guard-selftest.json` exercises the actual compiled validator;
  `check-diagnostic-guard.py` preserves the controlled test.
- Candidate manifest and verification record hashes, limits, ELF/bin
  consistency, driver tables and shared FIT payload integrity.

No hardware access or device storage writes were performed. Candidate
loaders and their full ELF/map files are outside the repository at the path
recorded in the report and are not hardware-validated repairs.
