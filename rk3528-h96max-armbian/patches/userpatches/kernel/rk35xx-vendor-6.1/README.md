# Overrides for the pinned H96 kernel baseline

Kernel commit: `4ee92c1e3bd78ddc6f57c5a9dc056281ea863072` (6.1.172).

The six empty patch files disable same-named framework patches because their complete changes already exist in this kernel commit. Verified individually with `patch --dry-run --batch -R -p1` against files extracted from the unpatched commit; all six reverse checks passed on 2026-11-03. Armbian supports empty userpatches as explicit overrides. The H96 extension pins the kernel commit so these overrides are not silently reused with a different branch tip.

These overrides retain the existing Sony HID, Bluetooth quirk, Eltay and Rock 2 SD changes. Re-evaluate them before changing the kernel baseline. Do not use IGNORE_PATCH_ERRORS to bypass failures.
