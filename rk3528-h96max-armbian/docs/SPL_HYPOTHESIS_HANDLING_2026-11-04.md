# SPL hypotheses: checks and handling — 2026-11-04

Scope: files, source code, host checks and controlled CPU emulation. No box,
SD card, eMMC, firmware partition or BootROM state was modified.

## Results by hypothesis

| Hypothesis | Additional check | Handling / current conclusion |
| --- | --- | --- |
| Wrong SPL/ELF or package used for analysis | All file-backed allocated ELF sections match the incident SPL binary. Incident DEB payloads match the source artifacts, retained SD first-16-MiB capture and hashes recorded during installation. A second cached DEB has different hashes but the same pointer location/value and fault-site instructions. | No mismatch found in the retained chain. The old UART trace has no binary fingerprint, so current runtime identity remains unproven. A distinct diagnostic ID and hash manifest address that ambiguity in prepared diagnostics. |
| Pointer already corrupt at SPL handoff | Supply the reported word before SPL entry in the emulator. | The first checkpoint already reports the bad word and the original binary fails at 0x9410. This validates that mechanism, not that the real loader delivered corrupt data. The diagnostic checks before cache enable, so an early failure can be distinguished from a later change. |
| CPU code overwrites the match table | Make its page read-only in emulator memory, run the normal path, then redirect a real memset CPU store to the field as a positive control. | Normal startup passes. The redirected store is caught at PC 0x95c4, address 0x31258, with WRITE_PROT and the original pointer intact. This proves the observer catches a CPU store; no such offending store was found in the real, unmodified path. |
| Allocation failure or overflow causes a wild write | Compile the actual vendor calloc body and exercise success, forced OOM, overflowing multiplication and zero size. | Two defects reproduced: NULL memset on OOM and unguarded multiplication overflow. Both are corrected and pass the same checks. Normal early boot uses 40336/524288 heap bytes, so OOM is not demonstrated as this crash's cause. |
| Incorrect MMU/TCR setup | Re-run the actual page-table construction algorithms with corrected unsigned constants. | Identity mapping/attributes pass 4096 boundary probes, canary intact. Supplied TCR_EL3 is 0x80803520 instead of sign-extended 0xffffffff80803520. Source corrected; actual hardware translation/cache behavior remains untested. |
| DDR timing/electrical instability | Keep the diagnostic SPL byte-for-byte identical and vary only the already-audited DDR3 frequency parameter, 1056 versus 528 MHz. | Both ordinary-file loader candidates built and verified. Static analysis cannot establish DDR stability or the correct PCB electrical variant. No automatic change to production DDR frequency is made. |
| Cache-dependent read/coherency behavior | Prepare diagnostic cache-on/off configurations differing only in CONFIG_SPL_SYS_DCACHE_OFF. | Both built and checked. Register/cache hardware effects are not emulated; these candidates do not establish whether cache caused the original fault. Stage checks distinguish a value already wrong before cache from a value first observed wrong afterward. |
| FIT/BL31 packaging error | Rebuild U-Boot, verify every FIT image/reference/hash and compare against the original incident FIT. | Found an independent host-build hazard: a missing Python 2 interpreter could silently omit ATF nodes while leaving firmware=atf-1. The original incident FIT contains all three BL31 segments, so this is not its early strcmp cause. Build scripts now use Python 3 and fail on decoder failure/missing BL31. A negative test confirms no dummy ELF is created. |

The earlier DTB checks remain valid: changing SFC compatible or its MMIO reg
does not change the stored driver string pointer in the tested early paths.

## Source fixes integrated into future image builds

Two patches are in the U-Boot patch directory used by this board:

- `h96-fix-early-calloc-and-tcr-width.patch`: check multiplication overflow
  and malloc failure in early calloc; use unsigned TCR masks.
- `h96-require-valid-bl31-fit.patch`: use the Python-3-compatible BL31
  decoder with Python 3; reject missing BL31; propagate extraction failures
  instead of generating a dangling FIT firmware reference.

`build-desktop.sh` now requires these files and stages them through its
existing patch-copy step. Both patches apply cleanly to the retained source.
The source changes were compiled in a separate tree; the incident source
cache and incident binary remain preserved for analysis. No full desktop
image or installable DEB was rebuilt in this round.

These fixes remove confirmed defects. They do not establish that the original
SFC abort is repaired. In particular, calloc protection is not a claim that
every possible OOM path in every vendor driver has been hardened.

## Diagnostic behavior and interpretation

The diagnostic SPL prints `H96-SPL-HYP-20261104-R1`. Its manifest associates
that ID with actual SPL hashes and ELF symbol addresses, rather than relying
on the old Armbian version banner. The private manual build retains an old
CONFIG_LOCALVERSION string; that version string alone is not a fingerprint.

Checks compare:

1. driver->of_match against the linked table address;
2. both stored compatible pointers against independently computed addresses
   of named character arrays;
3. the table terminator against NULL.

The validator reads words through explicit AArch64 loads, preventing the
compiler from substituting const initializers for the integrity comparison.
Generated code and controlled tests verify that a corrupted word actually
reaches the error branch. A bad table address is compared before dereferencing
it. The validator reports `H96-MATCH-CORRUPT`, its stage and expected/observed
values, then halts; it does not rewrite the value or bypass driver matching.

Stage checks run at board-init entry, around cache/FDT/DM initialization, at
node matching, and after device binding. Existing node/bind messages identify
the most recent driver callback. The abort handler also reports FAR/SP/SCTLR.

| First observation | What it establishes |
| --- | --- |
| Wrong before cache enable | Corruption predates cache setup; does not distinguish loading, DDR or an earlier operation by itself |
| Correct before cache, wrong after cache | First observed change is within that interval; still not proof that cache alone caused it |
| Correct before a node/callback, wrong afterward | Narrows the software/hardware interval to investigate |
| All checks correct but a later load/strcmp sees a bad value | Consider transient read/register/instruction/coherency effects; the table has not been proven persistently overwritten |

## Prepared artifacts and checks

Ordinary files are in `/home/nguyentiem/h96-hypotheses-20261104/`:

| Loader | Purpose |
| --- | --- |
| idbloader-hardened-ddr1056.img | production-source fixes, original standard DDR settings |
| idbloader-diagnostic-cache-on-ddr1056.img | fingerprint + stage/integrity checks, cache on |
| idbloader-diagnostic-cache-on-ddr528.img | identical diagnostic SPL, DDR3 frequency reduced only |
| idbloader-diagnostic-cache-off-ddr1056.img | same diagnostic source, cache off only |

`hardened/u-boot.itb` is the checked common next-stage payload. Each SPL
variant retains ELF/map/config files. All loaders retain DDR offset 2048 and
SPL offset 63488, and all SPL binaries fit within 0x40000 bytes. The diagnostic
addresses differ from the original build: use the paired ELF and manifest,
not the original 0x31258/0x9410 constants.

Validation completed:

- All three SPL ELF/bin pairs match; all driver tables are structurally valid.
- Shared FIT has five hash-verified payloads and valid configuration references.
- Patched calloc passes success/OOM/overflow/zero-size checks; original source
  reproduces the two negative outcomes.
- Patched MMU construction passes the 4096 boundary probes.
- Three guard self-tests pass: healthy returns; bad compatible word and bad
  table address halt diagnostically without an invalid dereference.
- Three additional incident-binary replay controls pass: corrupt at entry,
  read-only page with a redirected CPU store, normal read-only-page startup.
- Nine repository regression tests and shell syntax checks pass.

The earlier diagnostic package without this fingerprint is superseded for
this hypothesis investigation. Nothing in either package has been flashed.

Evidence, patches, manifests and test outcomes are in
`evidence/boot-hypotheses-2026-11-04/`. The candidate status is
**STATICALLY_VERIFIED_NOT_HARDWARE_TESTED**. The remaining uncertainty is
the original board's first corrupting event, not the location or meaning
of the faulting pointer load.
