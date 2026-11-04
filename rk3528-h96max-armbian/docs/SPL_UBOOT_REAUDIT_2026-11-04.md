# SPL/U-Boot re-audit — 2026-11-04

For the deeper source/binary pointer-write investigation and controlled CPU
replays, see [SPL pointer flow](SPL_POINTER_FLOW_2026-11-04.md).
The subsequent [hypothesis handling](SPL_HYPOTHESIS_HANDLING_2026-11-04.md)
records the source fixes now added to future builds and the separate diagnostic
artifacts. Statements below about unapplied candidate fixes describe the
earlier audit stage.

## Result

The retained bootloader targets the correct SoC, RK3528, but is configured for
Hinlink H28K/HT2 rather than a validated H96 Max board. This is a board bring-up
gap, not evidence of an RK3328/RK3568 binary being installed. The immediate
failure is an invalid pointer during SPL driver matching, before U-Boot proper
loads. A board-name change alone will not explain or repair it.

## Independently rechecked local evidence

Source/build directory relative to the project:
`armbian-build/cache/sources/u-boot-worktree/u-boot-rockchip64/next-dev-v2024.10/`.

- `.config`: `CONFIG_ROCKCHIP_RK3528=y`, `CONFIG_TARGET_EVB_RK3528=y`,
  `CONFIG_DEFAULT_DEVICE_TREE="rk3528-hinlink-h28k"`.
- Board layer sources `hinlink-ht2.csc`, inheriting
  `BOOTCONFIG=hinlink_rk3528_defconfig` and `BOOT_SCENARIO=spl-blobs`.
  `BOOT_FDT_FILE` selects the Linux DTB; it does not replace SPL's embedded DTB.
- Both `spl/u-boot-spl.dtb` and `u-boot.dtb` identify `Hinlink H28K`.
  SD at ffc30000 has a 150 MHz maximum; eMMC at ffbf0000 has a 200 MHz maximum.
  These are configured ceilings, not measured operating clocks.
- The shared U-Boot DTS enables eMMC HS400 and enhanced strobe, plus SFC
  NAND/NOR boot candidates. These features require board validation.
- DT stdout points to UART2 at ffa00000; debug UART uses UART0 at ff9f0000,
  mux 0, 115200 baud, with `CONFIG_DEBUG_UART_ALWAYS=y`.
- Family selection uses RK3528 DDR v1.09 at 1056 MHz and RK3528 BL31 v1.17.
  DDR training completion does not demonstrate stable RAM.
- SPL SHA-256 remains
  `6addd3cc424a94271e17a846a4a11752660ebca60cdae1e631357d59cff1d5ca`.
  Its binary length is 245892 bytes including the appended DTB.

## Crash interpretation

`aarch64-linux-gnu-addr2line` on the retained ELF confirms:

| UART value | Symbol/source |
| --- | --- |
| PC 0x9410 | strcmp, lib/string.c:189 |
| LR 0xe4f8 | driver_check_compatible, drivers/core/lists.c:116 |
| x23 0x39a58 | rockchip_sfc_driver linker-list entry |
| x24 0x31258 | rockchip_sfc_ids |

Disassembly loads the compatible pointer from `[x24]` into x0 before calling
strcmp. The binary contains the 64-bit value `0x28e6f` there, pointing to
`rockchip,fspi`. The previously recorded readable UART trace instead reports
x0/x4 = `0x0000300000027e6f`. Their XOR is `0x30000000f000`.
The pointer is non-NULL and differs from the binary. This supports a runtime
data-integrity investigation, but cannot distinguish DDR instability, an
overwrite, relocation problems, or another fault without new runtime evidence.
Encountering SFC in the driver matching loop does not prove SFC hardware was
accessed: `lists_bind_fdt` searches the driver table for node matches.

`U-Boot SPL board init` is printed in `board_init_f` immediately before
`spl_early_init`. This is consistent with failure during early driver-model
scanning. It is not evidence that `spl_board_init` completed. FIT loading and
Linux rootfs/DTB processing have not been reached in this crash.

The linked image ends at 0x3a9d8, below the configured SPL limit 0x40000;
BSS occupies 0x3fe0000..0x3fe09f0 and the initial stack top is 0x3fe0000.
These static ranges do not show an obvious image/BSS overlap. They do not
exclude runtime writes or allocation/stack errors.

## Full static memory and control-flow audit

The requested final scope is software logic and memory-map verification only.
The retained source is vendor U-Boot **2017.09**, despite the cache directory
being named `next-dev-v2024.10`. Directory names must not be used to infer the
code generation or upstream version.

### Physical and virtual map verified in both ELF files

Both the SPL ELF and U-Boot ELF contain exactly the map declared by RK3528 code:

| Range (end exclusive) | Mapping |
| --- | --- |
| 0x00000000..0xfc000000 | identity, normal cached RAM, inner shareable |
| 0xfc000000..0x100000000 | identity, Device-nGnRnE, execute-never |

The Android DTB captured from this actual box exposes Linux RAM at
0x00200000..0x08400000 and 0x08c00000..0xfc000000. Its upper RAM boundary
therefore agrees with the U-Boot RAM/MMIO split. Linux's omitted low 2 MiB
contains firmware reservations; that omission does not mean SPL at address
zero is outside physical RAM. The Android firmware's intermediate reserved
gap also does not make an identity map of the underlying physical RAM invalid.

All 14 shared `reg` nodes in the SPL DTB and all 20 shared `reg` nodes in the
U-Boot DTB match the captured Android DTB byte-for-byte. These counts include
the SCMI protocol identifier, not only MMIO nodes. In particular, eMMC
ffbf0000, SD ffc30000, SFC ffc00000, CRU ff4a0000, GRF ff300000, IOC ff540000,
crypto ffc40000 and ordinary OTP ffce0000 agree. The selected DT UART2 also
has the correct SoC address ffa00000; selecting UART0 for this board is a
console configuration issue, not a differing physical register map.

SFC flash child nodes and secure OTP ffcd0000 are additional U-Boot nodes
absent from the captured Android tree. Their absence is not evidence of a
wrong address, and their board applicability is not established by this DT
comparison.

### Page tables tested using the retained construction code

`tools/check-rk3528-mmu.py` extracts and compiles the actual `get_tcr`,
`find_pte`, `add_map`, table-size calculation and normal/emergency table
construction code, plus the RK3528 map and original MMU constants. It runs
those algorithms on host-allocated memory without ARM register operations.

- VA width: 32 bits, 4 KiB translation granule.
- Reserved page-table space: 32768 bytes; normal plus emergency tables use
  16384 bytes. The allocation canary remains intact.
- 4096 probes check both ends of every 2 MiB interval across the entire
  4 GiB address map. Identity translations, RAM/MMIO attributes and
  execute-never boundaries pass.
- The real table and string addresses 0x31258 and 0x28e6f are mapped RAM.
  The reported bad pointer 0x0000300000027e6f is outside the configured VA
  range. Expanding the map to accommodate it would conceal a bad pointer.

This verifies software arithmetic and allocation bounds, not actual hardware
cache/DDR behavior or runtime TCR contents.

### Concrete source defect: signed TCR masks

`arch/arm/include/asm/armv8/mmu.h:100..102` defines the reserved-bit masks
using signed `1 << 31`. With the retained compiler output this sign-extends
into 64 bits. The host check returns TCR_EL3 = **0xffffffff80803520**, and
the original SPL disassembly at 0x17bc/0x17c4 constructs the same extended
constant. This is not a host-only discrepancy.

Using `UL(1)` for these shifts yields **0x0000000080803520** and passes the
same 4096 mapping probes with unchanged table usage. A reviewable correction
is in `evidence/bootloader-audit-2026-11-04/tcr-unsigned-candidate.patch`;
it has not been applied to the production build.

The Cortex-A53 TRM describes TCR_EL3 as 32-bit. Consequently this is a
source-level width/undefined-shift defect, but the high half of the supplied
MSR value alone does **not** prove that the processor uses an incorrect VA
map or that this caused the SFC pointer corruption. The reserved upper bits
may not affect implemented translation behavior. The source correction is
not a confirmed crash repair. See [Arm Cortex-A53 TRM, section 4.3.57](https://documentation-service.arm.com/static/6040c321ee937942ba301626).

### Effective SPL layout

Ranges are end-exclusive; SPL addresses refer to its original linked image.

| Object | Address/range |
| --- | --- |
| SPL code/data/linker lists | 0x00000000..0x0003a9d8 |
| Appended SPL DTB | 0x0003a9d8..0x0003c084 |
| Global data, 448 bytes | 0x03f5fe40..0x03f60000 |
| Early heap, 512 KiB | 0x03f60000..0x03fe0000 |
| Page-table reservation within heap | 0x03f60000..0x03f68000 |
| Effective initial C stack | starts at 0x03f5fe40, grows downward |
| SPL BSS | 0x03fe0000..0x03fe09f0 |
| SCMI shared memory | 0x0010f000..0x0010f100 |
| ATAGS reserved window | 0x001fe000..0x00200000 |

The effective stack value includes heap/GD reservation; the configuration
macro 0x03fe0000 is the top **before** those reservations. The disassembly
at 0x39e8 confirms subtraction of 0x80000 and 0x1c0.
No overlap of the SPL image, initial stack/GD, heap, page tables, BSS or SCMI
buffer is evident. The appended DTB begins exactly at `_image_binary_end`,
matching `fdtdec_setup` with `CONFIG_SPL_SEPARATE_BSS=y`.

### FIT load ranges and a later scratch-buffer overlap

All five FIT SHA-256 values were recalculated from actual external data using
the vendor's **512-byte FIT alignment**. U-Boot and FDT match the retained
files exactly; each ATF segment matches the corresponding PT_LOAD segment
of RK3528 BL31 v1.17. The DDR and SPL placement inside idbloader was also
verified, and repacking reproduces the incident loader hash exactly.

| FIT payload | Load range |
| --- | --- |
| U-Boot | 0x00200000..0x003165d8 |
| BL31 first segment | 0x00080000..0x000a2d62 |
| BL31 second segment | 0xfe48d000..0xfe490000 |
| BL31 third segment | 0xfe490000..0xfe491c24 |

These payload ranges do not overlap one another or the SPL image/heap/BSS.
SPL disables caches and MMU before jumping to BL31, so the SPL device-memory
execute-never attributes do not govern subsequent firmware execution from
the BL31 SRAM segments.

However, examining the actual MMC/simple-FIT path reveals a **scratch-buffer
overlap with the reserved ATAGS window**:

- `spl_mmc.c` reads a 512-byte first sector at
  `CONFIG_SYS_TEXT_BASE - sizeof(struct image_header)` = 0x001fffc0,
  covering 0x001fffc0..0x002001c0.
- `spl_fit_load_blob` aligns the 0x7b3-byte FIT header to 0x800 bytes and
  places it at 0x001ff5c0, covering 0x001ff5c0..0x001ffdc0.
- Both touch the reserved ATAGS window 0x001fe000..0x00200000. The first
  read also crosses the future U-Boot load boundary, before U-Boot is loaded.

This is a real static region overlap, but not proof that currently live tags
are overwritten: the tag list may occupy only the beginning of the window.
It occurs later than the observed `strcmp` crash and cannot explain that
early failure. It should be accounted for when reviewing the complete
SPL-to-U-Boot handoff; a constant such as `CONFIG_SPL_LOAD_FIT_ADDRESS` alone
does not describe this actual MMC scratch-buffer path.

### Control-flow trace and remaining source risks

The source-compatible path to the observed abort is:

```text
_main -> reserve/zero GD -> board_init_f_boot_flags -> board_init_f
  -> spl_early_init -> spl_common_init
     -> allocate page tables / enable D-cache and MMU
     -> fdtdec_setup -> dm_init_and_scan
     -> lists_bind_fdt -> driver_check_compatible -> strcmp [abort]
```

This is an inferred source path, not a newly captured runtime stack. The
faulting byte load uses the compatible pointer read from the driver table,
not the SFC MMIO base. `CONFIG_SPL_SKIP_RELOCATE=y` and
`CONFIG_POSITION_INDEPENDENT` is disabled; the normal early path has no
legitimate relocation that turns the constant string pointer into the
reported high address. The match table is constant source data. Both the
ELF map and host page-table check make a wrong fixed MMIO base an unsupported
explanation for this particular instruction.

The vendor's `calloc` in `common/malloc_simple.c` also calls `memset` without
checking whether `malloc` returned NULL. On allocation failure, a nonzero
size could cause a write at address zero, where SPL is linked. This is a
real error-handling defect, not demonstrated heap exhaustion in this crash.
No evidence currently links it to the particular SFC table word at 0x31258.

All 29 SPL driver tables (71 compatible strings) and all 66 U-Boot driver
tables (161 strings) are structurally valid on disk. Four regression checks
pass, including deliberate substitution of the reported bad pointer and
one-bit FIT payload corruption; the audit rejects both corrupted inputs.

DDR electrical parameters remain board-specific: local standard, 2L_PCB and
4BIT_PCB v1.09 blobs differ in drive/ODT/skew settings. The 4BIT blob exports
DDR3 frequency 786 MHz, despite its filename containing 1056MHz. These
differences do not establish which variant belongs to this PCB, and static
analysis alone does not prove unstable DDR.

## Evidence and prepared diagnostics

Machine-readable results and source patches are under
`evidence/bootloader-audit-2026-11-04/`. Reproduce the main checks:

```sh
TREE=armbian-build/cache/sources/u-boot-worktree/u-boot-rockchip64/next-dev-v2024.10
python3 tools/audit-bootloader.py --uboot-tree "$TREE"
python3 tools/check-rk3528-mmu.py --uboot-tree "$TREE"
python3 tools/check-rk3528-mmu.py --uboot-tree "$TREE" --unsigned-tcr
python3 -m unittest discover -s tests -p test_bootloader_audit.py -v
```

Before the static-only scope clarification, three isolated trace loaders
were prepared at `/home/nguyentiem/h96-spl-trace-20261104/`: 1056 MHz with
D-cache on, 528 MHz with the same traced SPL, and 1056 MHz with D-cache off.
All fit the SPL size limit, retain the SPL offset, and include their ELF/map
files and hashes. The cache on/off configurations differ in only one setting.
They are not hardware-tested and contain no TCR correction. No production
loader source, disk sector, or device firmware was changed.

The static audit establishes that the broad RAM/MMIO mapping agrees with
the board evidence. It identifies the signed TCR mask defect, later FIT/ATAGS
scratch overlap, and unsafe calloc failure handling. It does not establish
which operation first produced the invalid pointer observed in the old log.
