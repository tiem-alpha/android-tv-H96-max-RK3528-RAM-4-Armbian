#!/usr/bin/env python3
"""Replay retained SPL early-init CPU code with modeled hardware side effects.

Requires unicorn==2.1.4 and capstone==5.0.9. This is a controlled software
experiment, not a full RK3528/DDR/cache model or a hardware crash capture.
"""
import sys, importlib.util, json, bisect, collections, struct, argparse, hashlib
from pathlib import Path
import unicorn as U
from unicorn import arm64_const as A
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--uboot-tree', type=Path, required=True)
parser.add_argument('--scenario', choices=['clean', 'poison-bss', 'serial-atags', 'bad-sfc-compatible', 'bad-sfc-reg', 'injected-pointer', 'poison-scratch', 'injected-dtb-argument', 'corrupt-at-entry', 'injected-cpu-store'], default='clean')
parser.add_argument('--el', type=int, choices=[2, 3], default=3)
parser.add_argument('--entry', choices=['start', 'main'], default='start')
parser.add_argument('--until', choices=['early-init', 'boot-order'], default='early-init')
parser.add_argument('--protect-match-page', action='store_true', help='make the SFC table page read-only in emulator memory')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location('audit', root / 'tools/audit-bootloader.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
tree = args.uboot_tree.resolve()
elf = m.Elf(tree / 'spl/u-boot-spl')
sym = elf.symbols
expected_sha = '6addd3cc424a94271e17a846a4a11752660ebca60cdae1e631357d59cff1d5ca'
if hashlib.sha256((tree / 'spl/u-boot-spl.bin').read_bytes()).hexdigest() != expected_sha:
    parser.error('This replay is pinned to the retained incident SPL; addresses must be re-audited for another build')
if sym['rockchip_sfc_ids'][0] != 0x31258 or sym['strcmp'][0] != 0x9408:
    parser.error('ELF symbols do not match the audited SPL ABI/addresses')
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.skipdata = True
instructions = {}
for _, kind, flags, base, off, size, *_ in elf.sections:
    if kind == 1 and flags & 4:
        instructions.update({i.address: i for i in md.disasm(elf.blob[off:off + size], base)})
funcs = sorted(((addr, addr + size, name) for name, (addr, size) in sym.items() if addr in instructions))
starts = [x[0] for x in funcs]

def name(pc):
    i = bisect.bisect_right(starts, pc) - 1
    if i >= 0 and pc < funcs[i][1]:
        return funcs[i][2]
    return hex(pc)
uc = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
uc.ctl_set_cpu_model(A.UC_CPU_ARM64_A53)
uc.mem_map(0, 0x4000000)
uc.mem_write(0, (tree / 'spl/u-boot-spl.bin').read_bytes())
uc.mem_map(0xfc000000, 0x4000000)
uc.mem_write(0xff9f0014, struct.pack('<I', 0x60))
uc.reg_write(A.UC_ARM64_REG_SP, 0xfe48b000 if args.entry == 'start' else 0x03fe0000)
initial_mutation = None
if args.scenario == 'corrupt-at-entry':
    uc.mem_write(0x31258, struct.pack('<Q', 0x300000027e6f))
    initial_mutation = 'Harness supplied an already-corrupt driver pointer before SPL entry'
if args.scenario == 'poison-scratch':
    uc.mem_write(0x03e00000, b'\xa5' * 0x1f0000)
    initial_mutation = 'Stack/GD/heap/BSS scratch filled with 0xa5 before normal initialization'
if args.scenario == 'poison-bss':
    uc.mem_write(0x3fe0000, b'\xa5' * 65536)
    initial_mutation = 'BSS filled with 0xa5 before its normal later clearing'
if args.scenario == 'serial-atags':
    core = struct.pack('<5I', 5, 0x54410001, 0, 0, 0)
    serial = struct.pack('<4IQ6I', 12, 0x54410050, 1, 1, 0xff9f0000, 1500000, 0, 0, 0, 0, 0)
    uc.mem_write(0x1fe000, core + serial + bytes(8))
    initial_mutation = 'Synthetic valid no-hash ATAG_SERIAL: UART0, 1500000 baud'
if args.scenario in ('bad-sfc-compatible', 'bad-sfc-reg'):
    dtb = (tree / 'spl/u-boot-spl.dtb').read_bytes()
    position = (tree / 'spl/u-boot-spl.bin').read_bytes().find(dtb)
    old, new = (b'rockchip,sfc\x00', b'rockchip,zzz\x00') if args.scenario == 'bad-sfc-compatible' else (struct.pack('>II', 0, 0xffc00000), struct.pack('>II', 0, 0xff000000))
    assert dtb.count(old) == 1
    dtb = dtb.replace(old, new)
    uc.mem_write(position, dtb)
    initial_mutation = args.scenario + '; same DTB byte length, no driver data changed'
if args.protect_match_page:
    uc.mem_protect(0x31000, 0x1000, U.UC_PROT_READ)

state = {'until': args.until, 'entry': args.entry, 'scenario': args.scenario, 'modeled_el': args.el, 'match_page_read_only': args.protect_match_page, 'initial_mutation': initial_mutation, 'binary_sha256': hashlib.sha256((tree / 'spl/u-boot-spl.bin').read_bytes()).hexdigest(), 'checkpoints': [], 'load_trace': [], 'write_regions': collections.Counter(), 'write_bounds': {}, 'target_writes': [], 'count': 0, 'stop': None, 'registers': {}, 'image_writes': [], 'target_reads': [], 'calls': collections.Counter(), 'stubs': collections.Counter(), 'sfc_compares': 0, 'recent': collections.deque(maxlen=20)}
skips = {'invalidate_dcache_all', '__asm_invalidate_tlb_all'}
stop_pc = None
sctlr = 0
injected = False
checkpoints = {'board_init_f', 'spl_early_init', 'spl_common_init.constprop.0', 'get_page_table_size', 'setup_pgtables', 'fdtdec_setup', 'dm_init_and_scan', 'dm_init', 'dm_scan_platdata', 'dm_extended_scan_fdt'}

def reg(r):
    return getattr(A, 'UC_ARM64_REG_' + r.upper())

def code(uc, pc, size, data):
    global stop_pc, sctlr, injected
    state['count'] += 1
    if (args.until == 'early-init' and pc == stop_pc) or (args.until == 'boot-order' and pc == sym['board_boot_order'][0]):
        state['stop'] = 'spl_early_init_return' if args.until == 'early-init' else 'board_boot_order_entry'
        state['return_register_x0'] = hex(uc.reg_read(A.UC_ARM64_REG_X0))
        uc.emu_stop()
        return
    fn = name(pc)
    state['recent'].append((hex(pc), fn))
    if fn in checkpoints and pc == sym[fn][0]:
        state['checkpoints'].append({'function': fn, 'pc': hex(pc), 'pointer': hex(int.from_bytes(uc.mem_read(0x31258, 8), 'little'))})
    if args.scenario == 'injected-cpu-store' and not injected and pc == sym['memset'][0] and 0x3f60000 <= uc.reg_read(A.UC_ARM64_REG_X0) < 0x3fe0000:
        uc.reg_write(A.UC_ARM64_REG_X0, 0x31258)
        uc.reg_write(A.UC_ARM64_REG_X1, 0xa5)
        uc.reg_write(A.UC_ARM64_REG_X2, 8)
        injected = True
        state['injection'] = {'pc': hex(pc), 'function': 'memset', 'destination': '0x31258', 'performed_by': 'test harness redirects a CPU store; not a discovered SPL bug'}
    if args.scenario == 'injected-pointer' and (not injected) and (pc == 0xe500) and (uc.reg_read(A.UC_ARM64_REG_X24) == 0x31258):
        uc.mem_write(0x31258, struct.pack('<Q', 0x300000027e6f))
        injected = True
        state['injection'] = {'pc': hex(pc), 'address': '0x31258', 'value': '0x0000300000027e6f', 'performed_by': 'test harness, not SPL'}
    if args.scenario == 'injected-dtb-argument' and not injected and pc == 0xe4f4 and uc.reg_read(A.UC_ARM64_REG_X24) == 0x31258:
        uc.reg_write(A.UC_ARM64_REG_X1, 0x300000027e6f)
        injected = True
        state['injection'] = {'pc': hex(pc), 'register': 'x1', 'value': '0x300000027e6f', 'performed_by': 'test harness, not SPL'}
    if pc in (0xe500, 0xe504, 0xe4f4, 0x9408, 0x940c, 0x9410) and uc.reg_read(A.UC_ARM64_REG_X24) == 0x31258:
        state['load_trace'].append({'pc': hex(pc), 'instruction': instructions[pc].mnemonic + ' ' + instructions[pc].op_str, 'x0': hex(uc.reg_read(A.UC_ARM64_REG_X0)), 'x4': hex(uc.reg_read(A.UC_ARM64_REG_X4)), 'x24': hex(uc.reg_read(A.UC_ARM64_REG_X24)), 'table_word': hex(int.from_bytes(uc.mem_read(0x31258, 8), 'little'))})
    if pc == sym.get('spl_early_init', (None,))[0]:
        stop_pc = uc.reg_read(A.UC_ARM64_REG_X30)
    if pc == sym.get('hang', (None,))[0]:
        state['stop'] = 'hang'
        uc.emu_stop()
        return
    if pc == sym.get('strcmp', (None,))[0] and uc.reg_read(A.UC_ARM64_REG_X30) == 0xe4f8:
        if uc.reg_read(A.UC_ARM64_REG_X24) == 0x31258:
            state['sfc_compares'] += 1
    if fn in skips and pc == sym[fn][0]:
        state['stubs'][fn] += 1
        if fn == 'get_ticks':
            uc.reg_write(A.UC_ARM64_REG_X0, state['count'])
        uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_X30))
        return
    i = instructions.get(pc)
    if not i:
        state['stop'] = 'unknown_instruction'
        uc.emu_stop()
        return
    if i.mnemonic in ('mrs', 'msr'):
        parts = [v.strip() for v in i.op_str.split(',')]
        if i.mnemonic == 'mrs':
            dst, sr = parts
            if sr == 'currentel':
                v = args.el * 4
            elif sr.startswith('sctlr_'):
                v = sctlr
            elif sr == 'cntfrq_el0':
                v = 24000000
            elif sr in ('cntpct_el0', 'cntvct_el0'):
                v = state['count']
            else:
                v = state['registers'].get(sr, 0)
            uc.reg_write(reg(dst), v)
        else:
            sr, src = parts
            v = int(src[1:], 0) if src.startswith('#') else uc.reg_read(reg(src)) if src != 'xzr' else 0
            state['registers'][sr] = v
            if sr.startswith('sctlr_'):
                sctlr = v
        uc.reg_write(A.UC_ARM64_REG_PC, pc + 4)
        return
    if i.mnemonic in ('dc', 'ic', 'tlbi'):
        uc.reg_write(A.UC_ARM64_REG_PC, pc + 4)
        return
    if i.mnemonic in ('bl', 'blr'):
        target = int(i.op_str.lstrip('#'), 16) if i.mnemonic == 'bl' else uc.reg_read(reg(i.op_str))
        state['calls'][fn, name(target)] += 1

def write(uc, access, addr, size, value, data):
    region = 'MMIO' if addr >= 0xfc000000 else 'image' if addr < 0x3c084 else 'heap' if 0x3f60000 <= addr < 0x3fe0000 else 'GD' if 0x3f5fe40 <= addr < 0x3f60000 else 'stack' if 0x3e00000 <= addr < 0x3f5fe40 else 'other_RAM'
    state['write_regions'][region] += 1
    bounds = state['write_bounds'].setdefault(region, [addr, addr + size])
    bounds[0] = min(bounds[0], addr)
    bounds[1] = max(bounds[1], addr + size)
    if addr < 0x31260 and addr + size > 0x31258:
        state['target_writes'].append({'pc': hex(uc.reg_read(A.UC_ARM64_REG_PC)), 'address': hex(addr), 'size': size, 'value': hex(value)})
    if addr < 0x3c084:
        state['image_writes'].append({'pc': hex(uc.reg_read(A.UC_ARM64_REG_PC)), 'function': name(uc.reg_read(A.UC_ARM64_REG_PC)), 'address': hex(addr), 'size': size, 'value': hex(value)})

def read(uc, access, addr, size, value, data):
    state['target_reads'].append({'pc': hex(uc.reg_read(A.UC_ARM64_REG_PC)), 'function': name(uc.reg_read(A.UC_ARM64_REG_PC)), 'address': hex(addr), 'value': uc.mem_read(addr, size).hex()})

def bad(uc, access, addr, size, value, data):
    state['stop'] = 'invalid_memory'
    state['bad_memory'] = {'address': hex(addr), 'pc': hex(uc.reg_read(A.UC_ARM64_REG_PC)), 'access': access, 'x0': hex(uc.reg_read(A.UC_ARM64_REG_X0)), 'x1': hex(uc.reg_read(A.UC_ARM64_REG_X1)), 'x4': hex(uc.reg_read(A.UC_ARM64_REG_X4)), 'lr': hex(uc.reg_read(A.UC_ARM64_REG_X30))}
    return False
uc.hook_add(U.UC_HOOK_CODE, code)
uc.hook_add(U.UC_HOOK_MEM_WRITE, write)
uc.hook_add(U.UC_HOOK_MEM_READ, read, begin=0x31258, end=0x3125f)
uc.hook_add(U.UC_HOOK_MEM_INVALID, bad)
try:
    uc.emu_start(0 if args.entry == 'start' else sym['_main'][0], 0x4000000, count=2000000)
except U.UcError as e:
    state['error'] = str(e)
state['write_bounds'] = {key: [hex(value[0]), hex(value[1])] for key, value in state['write_bounds'].items()}
state['heap_state'] = dict(zip(['malloc_base', 'malloc_limit', 'malloc_ptr'], struct.unpack('<3Q', uc.mem_read(uc.reg_read(A.UC_ARM64_REG_X18) + 288, 24))))
state['write_regions'] = dict(state['write_regions'])
state['final_pc'] = hex(uc.reg_read(A.UC_ARM64_REG_PC))
state['final_pointer'] = hex(int.from_bytes(uc.mem_read(0x31258, 8), 'little'))
state['calls'] = [{'caller': a, 'callee': b, 'count': c} for (a, b), c in state['calls'].items()]
state['stubs'] = dict(state['stubs'])
state['recent'] = list(state['recent'])
state['limitations'] = ['Starts at SPL entry or _main after DDR/BootROM handoff; initial BootROM SP is modeled', 'EL and system registers are modeled; ARM MMU/cache effects are not executed', 'Only cache/TLB invalidation functions are stubbed; UART0 LSR is modeled ready', 'MMIO reads default to zero except UART0 LSR=0x60; this is not a complete board model', 'No exhaustive exploration of arbitrary corrupt RAM/registers or external DMA']
print(json.dumps(state, indent=2))
