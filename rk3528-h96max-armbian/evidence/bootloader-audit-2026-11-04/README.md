# Static bootloader audit, 2026-11-04

See [the full analysis](../../docs/SPL_UBOOT_REAUDIT_2026-11-04.md).

- `static-audit.json`: driver-table pointers, embedded DTB properties, FIT
  hashes and payload load ranges, checked against the retained build.
- `board-memory-map.json`: shared DTB `reg` properties compared with the
  Android DTB captured from this box; also records Linux RAM/reservations.
- `elf-memory-maps.json`: RK3528 map data read directly from both ELF files.
- `mmu-host-check.json`: the actual retained page-table construction algorithms
  run on host memory. Mapping checks pass, but the signed TCR masks produce
  nonzero upper bits in the supplied TCR value.
- `mmu-unsigned-tcr-check.json`: the same host check with unsigned TCR masks.
- `tcr-unsigned-candidate.patch`: proposed three-line source correction,
  not applied to the production source or hardware.
- `payload-provenance.json`: FIT U-Boot/FDT comparison, ATF segments compared
  with the vendor BL31 ELF, and incident idbloader reproduction checks.
- `idb-header-check.json`: IDB v2 header and both padded payload hashes verified.
- DDR parameter exports and `ddr-variant-differences.json`: read-only exports
  using Rockchip ddrbin_tool v1.19. File names do not establish the effective
  DDR3 frequency or the correct board variant.
- `spl-memory-trace.patch` and `trace-manifest.json`: isolated diagnostics
  prepared before the user clarified the final scope as static analysis only.
  No trace loader was flashed or hardware-tested.

The checks validate software structure and mapping logic; they do not prove
electrical DDR stability, board wiring, cache coherency, or runtime registers.
