"""Exercise the audit against real retained artifacts and controlled corruption."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('audit', ROOT / 'tools/audit-bootloader.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
TREE = ROOT / 'armbian-build/cache/sources/u-boot-worktree/u-boot-rockchip64/next-dev-v2024.10'


@unittest.skipUnless((TREE / 'spl/u-boot-spl').exists(), 'retained vendor build required')
class AuditTests(unittest.TestCase):
    def test_retained_driver_tables(self):
        for name in ('spl/u-boot-spl', 'u-boot'):
            drivers = AUDIT.driver_audit(AUDIT.Elf(TREE / name))
            sfc = next(x for x in drivers if x['driver'] == 'rockchip_sfc_driver')
            self.assertEqual(sfc['matches'][0]['compatible'], 'rockchip,fspi')

    def test_reported_runtime_pointer_is_rejected(self):
        elf = AUDIT.Elf(TREE / 'spl/u-boot-spl')
        driver = elf.symbols['_u_boot_list_2_driver_2_rockchip_sfc_driver'][0]
        table = elf.pointer(driver + 16)
        blob = bytearray(elf.blob)
        for _, kind, flags, base, offset, size, *_ in elf.sections:
            if flags & 2 and kind != 8 and base <= table < base + size:
                struct.pack_into('<Q', blob, offset + table - base, 0x0000300000027e6f)
                break
        else:
            self.fail('match table not found')
        elf.blob = bytes(blob)
        with self.assertRaisesRegex(ValueError, 'outside file-backed'):
            AUDIT.driver_audit(elf)

    def test_fit_hashes_and_load_ranges(self):
        result = AUDIT.fit_audit(TREE / 'u-boot.itb')
        self.assertEqual(len(result['images']), 5)
        self.assertTrue(result['load_ranges_disjoint'])

    def test_tampered_fit_is_rejected(self):
        path = TREE / 'u-boot.itb'
        result = AUDIT.fit_audit(path)
        blob = bytearray(path.read_bytes())
        blob[result['images'][0]['file_offset'] + 64] ^= 1
        with tempfile.TemporaryDirectory(prefix='h96-fit-test-') as directory:
            candidate = Path(directory) / 'tampered.itb'
            candidate.write_bytes(blob)
            with self.assertRaisesRegex(ValueError, 'FIT hash mismatch'):
                AUDIT.fit_audit(candidate)

    def test_missing_firmware_reference_is_rejected(self):
        blob = bytearray((TREE / 'u-boot.itb').read_bytes())
        # Rename only the image node; retain the configuration's atf-1 reference
        # and every payload/hash unchanged, reproducing a dangling FIT firmware.
        position = blob.index(b'atf-1\0')
        blob[position:position + 5] = b'bad-1'
        with tempfile.TemporaryDirectory(prefix='h96-fit-reference-') as directory:
            candidate = Path(directory) / 'missing-atf.itb'
            candidate.write_bytes(blob)
            with self.assertRaisesRegex(ValueError, 'missing firmware'):
                AUDIT.fit_audit(candidate)


if __name__ == '__main__':
    unittest.main()
