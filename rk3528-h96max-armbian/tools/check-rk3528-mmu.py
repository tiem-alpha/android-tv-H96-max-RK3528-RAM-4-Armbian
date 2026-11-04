#!/usr/bin/env python3
"""Run the retained RK3528 page-table construction C code on the host.

This checks software mapping arithmetic and table allocation, not ARM hardware,
cache coherency, DDR timing, or actual runtime register values.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot-tree', type=Path, required=True)
    parser.add_argument('--unsigned-tcr', action='store_true',
                        help='test the proposed unsigned TCR macro correction in host memory only')
    args = parser.parse_args()
    tree = args.uboot_tree.resolve()
    source = (tree / 'arch/arm/cpu/armv8/cache_v8.c').read_text()
    # Keep the actual TCR calculation, map construction, page-table sizing and
    # normal/emergency table creation algorithms, with no ARM assembly.
    algorithms = source[source.index('u64 get_tcr('):source.index('/* to activate the MMU')]
    header = (tree / 'arch/arm/include/asm/armv8/mmu.h').read_text()
    macros = header.split('#define _ASM_ARMV8_MMU_H_', 1)[1].split('#ifndef __ASSEMBLY__', 1)[0]
    if args.unsigned_tcr:
        for old, new in [('(1 << 31)', '(UL(1) << 31)'),
                         ('(1 << 31 | 1 << 23)', '(UL(1) << 31 | UL(1) << 23)')]:
            macros = macros.replace(old, new)
    soc = (tree / 'arch/arm/mach-rockchip/rk3528/rk3528.c').read_text()
    start = soc.index('static struct mm_region rk3528_mem_map[]')
    mapping = soc[start:soc.index('\n};', start) + 3]
    preamble = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned long long u64;
typedef unsigned long ulong;
#define UL(x) x##UL
#define __weak
#define max(a,b) ((a) > (b) ? (a) : (b))
#define min(a,b) ((a) < (b) ? (a) : (b))
#define pr_debug(...) do {} while (0)
static void panic(const char *fmt, ...) {
 va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); abort();
}
struct mm_region {u64 virt, phys, size, attrs;};
struct global_data {struct {u64 tlb_addr, tlb_fillptr, tlb_size, tlb_emerg;} arch;};
static struct global_data global;
static struct global_data *gd = &global;
'''
    harness = r'''
static u64 descriptor(u64 address, u64 va_bits) {
 if (address >= (1ULL << va_bits)) return 0;
 for (int level = va_bits < 39 ? 1 : 0; level < 4; level++) {
  u64 *pte = find_pte(address, level);
  if (!pte || !(*pte & 1)) return 0;
  if (level == 3 || pte_type(pte) == PTE_TYPE_BLOCK) {
   u64 mask = (1ULL << level2shift(level)) - 1;
   u64 phys = (*pte & 0x0000fffffffff000ULL & ~mask) | (address & mask);
   assert(phys == address);
   return *pte;
  }
 }
 abort();
}
int main(void) {
 u64 va_bits, ips;
 u64 tcr = get_tcr(3, &ips, &va_bits);
 assert(va_bits == 32 && ips == 0);
 size_t size = get_page_table_size();
 void *buffer;
 assert(posix_memalign(&buffer, 16384, size + 4096) == 0);
 memset(buffer, 0xa5, size + 4096);
 gd->arch.tlb_addr = (uintptr_t)buffer;
 gd->arch.tlb_size = size;
 setup_all_pgtables();
 size_t used = gd->arch.tlb_fillptr - gd->arch.tlb_addr;
 assert(used <= size);
 for (size_t i = size; i < size + 4096; i++)
  assert(((unsigned char *)buffer)[i] == 0xa5);
 // Check both ends of every 2 MiB interval across the entire 4 GiB map.
 unsigned checks = 0;
 for (u64 base = 0; base < (1ULL << 32); base += 0x200000) {
  for (int end = 0; end < 2; end++) {
   u64 addr = base + (end ? 0x1fffff : 0);
   u64 pte = descriptor(addr, va_bits);
   assert(pte);
   assert(((pte >> 2) & 7) == (addr < 0xfc000000 ? MT_NORMAL : MT_DEVICE_NGNRNE));
   assert((pte & (PTE_BLOCK_PXN | PTE_BLOCK_UXN)) ==
          (addr < 0xfc000000 ? 0 : PTE_BLOCK_PXN | PTE_BLOCK_UXN));
   checks++;
  }
 }
 assert(descriptor(0x31258, va_bits));
 assert(descriptor(0x28e6f, va_bits));
 assert(!descriptor(0x0000300000027e6fULL, va_bits));
 printf("{\"status\":\"HOST_MAPPING_ARITHMETIC_PASS\",\"va_bits\":%llu,"
        "\"tcr_el3\":\"0x%llx\",\"table_reserved_bytes\":%zu,"
        "\"tcr_el3_upper_32_bits_nonzero\":%s,"
        "\"normal_and_emergency_table_used_bytes\":%zu,\"boundary_checks\":%u,"
        "\"identity_mapping\":true,\"ram_mmio_attributes\":true,"
        "\"allocation_canary_intact\":true,\"crash_pointer_outside_va\":true}\n",
        va_bits, tcr, size, (tcr >> 32) ? "true" : "false", used, checks);
 free(buffer);
}
'''
    with tempfile.TemporaryDirectory(prefix='h96-mmu-') as directory:
        work = Path(directory)
        code = work / 'mmu-check.c'
        code.write_text(preamble + macros + mapping +
                        '\nstruct mm_region *mem_map = rk3528_mem_map;\n' + algorithms + harness)
        subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra',
                        '-Wno-unused-parameter', '-Wno-sign-compare', '-Werror',
                        str(code), '-o', str(work / 'mmu-check')], check=True)
        subprocess.run([str(work / 'mmu-check')], check=True)


if __name__ == '__main__':
    main()
