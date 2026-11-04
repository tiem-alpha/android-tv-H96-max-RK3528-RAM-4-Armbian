"""Non-destructive regression checks for migration guards and boot configuration."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('install_emmc', Path(__file__).resolve().parents[1] / 'tools/install-emmc.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class MigrationGuards(unittest.TestCase):
    def test_spl_incident_blocks_install_and_resume_before_device_access(self):
        with patch.object(installer, 'preflight') as preflight:
            for resume in (False, True):
                with self.assertRaisesRegex(RuntimeError, 'eMMC writes disabled'):
                    installer.install('150100435742443352009bfe51d35200', resume=resume)
            preflight.assert_not_called()

    def test_nested_mounted_partition_is_rejected(self):
        disk = {'mountpoints': [], 'children': [{'mountpoints': []}, {'mountpoints': ['/mounted/android']}]}
        self.assertFalse(installer.all_unmounted(disk))
        disk['children'][1]['mountpoints'] = []
        self.assertTrue(installer.all_unmounted(disk))

    def target_fixture(self, directory):
        root = Path(directory) / 'target'
        (root / 'boot/dtb/rockchip').mkdir(parents=True)
        (root / 'etc/udev/rules.d').mkdir(parents=True)
        (root / 'etc/fstab').write_text(
            'UUID=sd-root / ext4 defaults 0 1\nUUID=sd-boot /boot ext4 defaults 0 2\n'
            'tmpfs /tmp tmpfs defaults 0 0\n')
        (root / 'etc/udev/rules.d/99-h96-emmc-detect.rules').write_text('detection-only read-only rule\n')
        active = Path(directory) / 'source.dtb'
        active.write_bytes(b'unchanged-source-DTB')
        original = installer.MOUNT
        installer.MOUNT = root
        self.addCleanup(setattr, installer, 'MOUNT', original)
        return root, active

    def test_target_uuid_rewrite_preserves_source_and_other_mounts(self):
        with tempfile.TemporaryDirectory() as directory:
            root, active = self.target_fixture(directory)
            source_env = 'verbosity=8\nrootdev=UUID=sd-root\nrootfstype=ext4\nfdtfile=rockchip/sd.dtb\nbootlogo=true\n'
            installer.configure('emmc-root', 'emmc-boot', source_env, active)
            target_env = (root / 'boot/armbianEnv.txt').read_text()
            self.assertIn('rootdev=UUID=emmc-root\n', target_env)
            self.assertNotIn('sd-root', target_env)
            self.assertIn('emmc.dtb', target_env)
            self.assertIn('bootlogo=false\n', target_env)
            fstab = (root / 'etc/fstab').read_text()
            self.assertIn('UUID=emmc-root\t/\t', fstab)
            self.assertIn('UUID=emmc-boot\t/boot\t', fstab)
            self.assertIn('tmpfs /tmp tmpfs defaults 0 0', fstab)
            self.assertEqual(active.read_bytes(), b'unchanged-source-DTB')
            self.assertIn('rootdev=UUID=sd-root', source_env)
            self.assertFalse((root / 'etc/udev/rules.d/99-h96-emmc-detect.rules').exists())

    def test_missing_boot_fstab_entry_stops_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root, active = self.target_fixture(directory)
            (root / 'etc/fstab').write_text('UUID=sd-root / ext4 defaults 0 1\n')
            with self.assertRaisesRegex(RuntimeError, 'root/boot entries missing'):
                installer.configure('emmc-root', 'emmc-boot', 'rootdev=UUID=sd-root\n', active)


if __name__ == '__main__':
    unittest.main()
