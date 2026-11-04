from pathlib import Path
import importlib.util,json,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID
from unicorn import arm64_const as A
root=Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('audit',root/'tools/audit-bootloader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
tree=Path('/home/nguyentiem/h96-hypotheses-20261104/diagnostic-cache-on');elf=m.Elf(tree/'u-boot-spl');sy=elf.symbols;rows=[]
for case in ['healthy','bad-compatible-word','bad-table-address']:
 uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);uc.ctl_set_cpu_model(A.UC_CPU_ARM64_A53);uc.mem_map(0,0x4000000);uc.mem_write(0,(tree/'u-boot-spl.bin').read_bytes());uc.reg_write(A.UC_ARM64_REG_SP,0x3f5fe40);uc.reg_write(A.UC_ARM64_REG_X18,0x3f5fe40);uc.reg_write(A.UC_ARM64_REG_X30,0x3e00000);uc.reg_write(A.UC_ARM64_REG_X0,0x3f60000);uc.mem_write(0x3f60000,b'guard-selftest\0');r={'case':case,'messages':[],'invalid_access':False}
 if case=='bad-compatible-word':uc.mem_write(sy['rockchip_sfc_ids'][0],struct.pack('<Q',0x300000027e6f))
 if case=='bad-table-address':uc.mem_write(sy['_u_boot_list_2_driver_2_rockchip_sfc_driver'][0]+16,struct.pack('<Q',0x300000027e6f))
 def code(uc,pc,size,data):
  if pc==0x3e00000:r['stop']='returned';uc.emu_stop()
  elif pc==sy['hang'][0]:r['stop']='diagnostic-halt';uc.emu_stop()
  elif pc==sy['printascii'][0]:
   addr=uc.reg_read(A.UC_ARM64_REG_X0);text=bytes(uc.mem_read(addr,160)).split(b'\0',1)[0].decode();r['messages'].append(text);uc.reg_write(A.UC_ARM64_REG_PC,uc.reg_read(A.UC_ARM64_REG_X30))
  elif pc==sy['printhex8'][0]:uc.reg_write(A.UC_ARM64_REG_PC,uc.reg_read(A.UC_ARM64_REG_X30))
 def invalid(uc,access,address,size,value,data):r['invalid_access']=True;return False
 uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_INVALID,invalid);uc.emu_start(sy['h96_sfc_validate'][0],0x4000000,count=10000);assert not r['invalid_access'];assert r['stop']==('returned' if case=='healthy' else 'diagnostic-halt');rows.append(r)
(root/'evidence/boot-hypotheses-2026-11-04/diagnostic-guard-selftest.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
