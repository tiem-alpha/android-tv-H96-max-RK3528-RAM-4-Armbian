# SPL compatible-pointer flow audit — 2026-11-04

## Finding

The retained SPL has no legitimate operation that transforms the compatible
pointer `0x28e6f` into `0x0000300000027e6f` on the checked startup paths.
The invalid value in the old UART trace reaches `strcmp` directly from a
64-bit load; no pointer arithmetic, DTB decoding or conversion intervenes.

This investigation combines source review, preprocessing with the retained
SPL build flags, original AArch64 disassembly, and controlled execution of
the original binary with memory-write hooks. It finds no responsible SPL
store on the modeled paths. It does **not** identify the real first corrupting
event on the board; physical DDR, cache behavior and BootROM/DDR execution
are outside the model.

## Exact object identity and value flow

The original SPL SHA-256 is
`6addd3cc424a94271e17a846a4a11752660ebca60cdae1e631357d59cff1d5ca`.

| Object | Address | Original contents |
| --- | --- | --- |
| rockchip_sfc_driver | 0x39a58 | driver structure, 120 bytes |
| driver->of_match field | 0x39a68 | 0x31258 |
| rockchip_sfc_ids[0].compatible | 0x31258 | 0x28e6f |
| string | 0x28e6f | `rockchip,fspi` |
| rockchip_sfc_ids[1].compatible | 0x31268 | 0x28e7d |
| second string | 0x28e7d | `rockchip,sfc` |

The table is declared `static const struct udevice_id` in
`drivers/spi/rockchip_sfc.c:927`. It is initialized by the compiler/linker,
not built from the DTB. A binary search finds the 64-bit table address only
in the driver field at 0x39a68, and the first string pointer only at 0x31258.
The reported bad pointer is absent from the binary. All 29 linker-list
driver records are contiguous with the expected 120-byte stride.

The actual instruction sequence is:

```text
0xe4e0  ldr  x24, [x23, #16]   ; driver->of_match
0xe500  ldr  x0, [x24]         ; of_match->compatible
0xe504  cbnz x0, 0xe4f0
0xe4f0  mov  x1, x26           ; separate compatible string from DTB
0xe4f4  bl   0x9408            ; strcmp; LR becomes 0xe4f8
0x9408  mov  x4, x0
0x940c  mov  x3, #0
0x9410  ldrb w5, [x4, x3]      ; first input: driver string [fault]
0x9414  ldrb w2, [x1, x3]      ; second input: DTB string
```

Therefore the observed PC 0x9410 and x0/x4 implicate the driver-side input,
not the DTB-side input x1. A hypothetical bad DTB string pointer produces a
different faulting instruction, 0x9414, in the controlled experiment.

The compatible-table loop increments **x24 by 16** to examine another entry;
it does not increment or rewrite the stored string-pointer word. `strcmp`
uses x3 as its byte offset and does not rewrite x0 or the table.

Original versus reported pointer bytes, little endian:

```text
original: 6f 8e 02 00 00 00 00 00
reported: 6f 7e 02 00 00 30 00 00
XOR:      00 f0 00 00 00 30 00 00
```

This is not a simple endian swap, pointer truncation, or normal table stride.
The byte difference is descriptive evidence, not proof of a particular
electrical failure. The old trace contains registers, not a dump of the
eight bytes at 0x31258 at the time of failure.

## Call paths that reach this load

In this configuration `driver_check_compatible` is inlined into
`lists_bind_fdt`. The compiled SPL takes the flat-FDT path; live-tree scanning
and OF_PLATDATA alternatives are excluded by SPL preprocessing.

```text
_start -> reset -> save_boot_params -> setjmp(brom_ctx)
       -> save_boot_params_ret -> lowlevel_init -> _main

_main
  -> board_init_f_alloc_reserve
  -> board_init_f_init_reserve       [clears GD, assigns heap base]
  -> board_init_f_boot_flags         [reads optional ATAG_SERIAL]
  -> board_init_f
     -> timer/debug UART setup
     -> spl_early_init
        -> spl_common_init
           -> memalign_simple / get_page_table_size / dcache_enable
              -> mmu_setup / setup_pgtables
           -> fdtdec_setup
           -> dm_init_and_scan
              -> dm_init / root binding
              -> dm_scan_platdata / lists_bind_drivers
              -> dm_extended_scan_fdt
                 -> dm_scan_fdt -> dm_scan_fdt_node
                    -> lists_bind_fdt
                       -> driver_check_compatible -> strcmp
                       -> device_bind_with_driver_data
                          -> device_bind_common
                             -> uclass_bind_device
                             -> driver->bind
                             -> parent->child_post_bind
                             -> uclass->post_bind
                 -> dm_scan_fdt_node for /clocks
              -> dm_scan_other
     -> preloader_console_init / serial_init / puts
     -> spl_hotkey_init / brom_download / arch_cpu_init / rk_board_init_f
  -> clear BSS
  -> board_init_r
     -> spl_initr_dm                 [empty with SPL_SKIP_RELOCATE]
     -> spl_set_bd / spl_init        [early-init flag skips another common init]
     -> timer_init / spl_board_init
     -> board_boot_order             [extended replay stops at this entry]
```

Recursive scanning from `dm_scan_fdt_dev` returns to the same
`dm_scan_fdt_node -> lists_bind_fdt` path. The binding callbacks observed in
the unmodified replay are:

| Callback | Relevant behavior |
| --- | --- |
| dm_scan_fdt_dev | recursively scans firmware/syscon/simple-bus children |
| rk3528_clk_bind | binds reset devices; allocates their private structures in heap |
| rockchip_sdhci_bind | creates eMMC block-layer device structures |
| rockchip_dwmmc_bind | creates SD block-layer device structures |
| spinand_bind | creates a block-layer device; does not probe NAND here |
| spi_flash_std_bind | creates a block-layer device; does not read flash here |
| spi_child_post_bind | decodes SPI child properties into allocated parent data |
| spi_flash_post_bind | returns success |
| pinctrl_post_bind / pinconfig_post_bind | binds pin configuration children |

The SFC driver's `.probe` and `.ofdata_to_platdata` functions do not execute
in the early binding replay. Changing its MMIO `reg` does not alter the
driver-table lookup. The clean run extended to boot-order entry records 182
distinct caller/callee edges; the complete observed call graph and counts
are in the corresponding JSON, including indirect calls.

## Possible writers and why they do or do not reach this object

| Candidate | Result for the retained configuration |
| --- | --- |
| Compiler/linker initializer | sole intended initial value of the word; correct in ELF/bin/IDB |
| BootROM/DDR loading | precedes modeled SPL entry; original runtime handoff state is unavailable |
| PIE fixup at reset | POSITION_INDEPENDENT is disabled; ELF has no relocations |
| relocate_code | linked but not taken on the checked path; SPL_SKIP_RELOCATE is enabled |
| fix_drivers | excluded by preprocessing; it would change the driver's table address, not rewrite this inner string pointer |
| setjmp(brom_ctx) | writes 104 bytes at 0x2ad40..0x2ada8, with no overlap at 0x31258 |
| GD initialization | clears 448 bytes at 0x3f5fe40; assigns heap base 0x3f60000 |
| Page-table construction | allocates/writes within heap; no alias to the low SPL image in the verified identity map |
| malloc/calloc and list/device setup | normal writes remain in heap, stack and GD; no store to the match table |
| DTB processing | reads the appended FDT and writes allocated device structures; no driver-constant rewrite |
| UART/timer/SoC register writes | modeled normal destinations are SRAM/MMIO; UART output code itself is executed, not skipped |
| BSS clearing | later than early matching; its fixed range 0x3fe0000..0x3fe09f0 does not overlap the table |
| MMC/FIT/crypto DMA | storage loading is later; not executed before the modeled first binding comparisons |

Preprocessing used the original `.o.cmd` compiler flags, including
`CONFIG_SPL_BUILD`, without rebuilding the retained objects. In the seven
relevant preprocessed translation units, no runtime `->of_match =` assignment
or definition of `fix_drivers` remains.

Generic wild writes remain possible if their **input pointer is already
corrupt**. For example, UART output accepts `gd->serial.addr` from
ATAG_SERIAL without proving it is a UART MMIO address. Corrupt inherited
state could therefore redirect a store, but the captured UART banner and
the checked valid ATAGS path do not demonstrate that situation. This must
not be reported as the discovered cause.

The unsafe calloc failure handling identified earlier is also real, but
the checked normal path uses only 40336 of 524288 heap bytes. No allocation
failure was observed, and memset at NULL would initially target address
zero, not the SFC pointer word. The TCR signed-mask defect and later
FIT/ATAGS scratch overlap likewise do not provide an identified write to
this word before early binding.

## Controlled binary experiments

The tool `tools/replay-spl-early.py` is pinned to the incident SPL hash and
checks the expected ELF addresses before running. It executes AArch64 CPU
instructions using Unicorn with a Cortex-A53 CPU selection. Every CPU memory
write is hooked, including writes outside the watched word.

| Experiment | Result |
| --- | --- |
| Original binary, modeled EL3 | early init returns, pointer 0x28e6f |
| Original binary, modeled EL2 | same |
| Initial BSS filled with 0xa5 | same |
| Synthetic valid ATAG_SERIAL, UART0 at 1.5 Mbps | same |
| SFC compatible changed to an unmatched string | SFC remains unmatched, no pointer corruption |
| SFC reg changed to ff000000 in the DTB copy | early binding still completes, no pointer corruption |
| Clean run through BSS clearing into board_init_r | reaches boot-order entry, pointer unchanged |
| Stack/GD/heap/BSS scratch filled with 0xa5 | reaches boot-order entry, pointer unchanged |
| Inject reported bad word at 0x31258 immediately before its load | invalid read at PC 0x9410, address 0x300000027e6f |
| Instead inject the bad value only into DTB argument x1 | invalid read at PC 0x9414; driver word remains 0x28e6f |

No SPL instruction writes the watched word in the eight non-injection runs.
The only writes inside the loaded SPL image on those paths are the 13
eight-byte store events from setjmp, entirely inside brom_ctx. Stack writes
reach down to 0x3f5f8d0, still far from the table; heap writes finish at
0x3f69d90 on the normal path. Filling scratch with 0xa5 checks one additional
initial-state pattern, not every possible uninitialized-memory state.

The table-word fault injection is performed by the test harness, explicitly
recorded as such. It reproduces the same attempted memory read and PC, not
the board's original corrupting store or an architectural ESR exception.

### Model limits

- BootROM and the proprietary DDR binary are not executed.
- Initial BootROM SP, current EL, counter values and system registers are modeled.
- UART/timer code runs against memory-backed register values; this is not a
  full UART, CRU or peripheral implementation.
- Cache/TLB invalidation operations and physical MMU/cache behavior are not
  emulated. Ordinary software page-table creation still executes.
- There is no electrical DDR fault model, external DMA actor, interrupt
  scheduling, or exhaustive exploration of arbitrary corrupted inputs.
- Normal runs stop before storage probing/loading. Their recorded lack of
  writes is scoped to the executed path, not every possible later SPL path.

These limitations mean the experiments can disprove a proposed direct
software transformation on the tested path, but cannot prove that the real
board has no overwrite or hardware-state problem.

## Reproduction and evidence

All run results, original instruction-level load traces, full observed call
graphs, reference locations and preprocessing records are under
`evidence/spl-pointer-flow-2026-11-04/`.

```sh
python3 -m venv /tmp/h96-spl-analysis-venv
/tmp/h96-spl-analysis-venv/bin/pip install unicorn==2.1.4 capstone==5.0.9
TREE=armbian-build/cache/sources/u-boot-worktree/u-boot-rockchip64/next-dev-v2024.10
/tmp/h96-spl-analysis-venv/bin/python tools/replay-spl-early.py --uboot-tree "$TREE"
/tmp/h96-spl-analysis-venv/bin/python tools/replay-spl-early.py --uboot-tree "$TREE" --scenario injected-pointer
/tmp/h96-spl-analysis-venv/bin/python tools/replay-spl-early.py --uboot-tree "$TREE" --scenario injected-dtb-argument
/tmp/h96-spl-analysis-venv/bin/python tools/replay-spl-early.py --uboot-tree "$TREE" --scenario poison-scratch --until boot-order
```

No production bootloader file, source configuration or device storage was
modified by this investigation. DTB changes and fault injection exist only
inside the emulator's memory.
