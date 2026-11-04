import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PlatformRunTests(unittest.TestCase):
    def test_ubuntu_run_uses_platform_runner_and_image(self):
        for platform, image, runner in [
            ("x86_64", "work/ubuntu-x86.img", "test/run-x86-ub.sh gui"),
            ("riscv64", "work/ubuntu-gui.img", "-cpu rv64"),
        ]:
            with self.subTest(platform=platform):
                result = subprocess.run(
                    ["make", "-n", "-o", "build", "-o", image,
                     f"PLATFORM={platform}", "ubuntu-run"],
                    cwd=ROOT, text=True, capture_output=True, check=True,
                )
                self.assertIn(image, result.stdout)
                self.assertIn(runner, result.stdout)
                if platform == "x86_64":
                    self.assertNotIn("qemu-system-riscv64", result.stdout)
                    self.assertIn("NOBUILD=1", result.stdout)

    def test_ubuntu_image_uses_platform_builder(self):
        for platform, builder in [
            ("x86_64", "test/ubuntu-x86/build-img.sh"),
            ("riscv64", "test/ubuntu-gui/build-img.sh"),
        ]:
            result = subprocess.run(
                ["make", "-n", f"PLATFORM={platform}", "ubuntu-image"],
                cwd=ROOT, text=True, capture_output=True, check=True,
            )
            self.assertIn(builder, result.stdout)

    def test_x86_console_selects_matching_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test").mkdir()
            shutil.copy(ROOT / "test/run.sh", root / "test/run.sh")
            target = root / "target/x86_64-unknown-none/debug"
            target.mkdir(parents=True)
            (target / "rux").touch()
            (target / "bzImage").touch()
            (root / "target/.build_features.x86_64").write_text("x86_64\n")
            (root / "test/rootfs-x86_64.img").touch()
            qemu = root / "qemu-system-x86_64"
            qemu.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            qemu.chmod(0o755)
            env = dict(os.environ, PLATFORM="x86_64", PATH=f"{root}:{os.environ['PATH']}")
            env.pop("ROOTFS_IMG", None)
            result = subprocess.run(
                ["bash", str(root / "test/run.sh"), "console", "/bin/sh"],
                env=env, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("q35\n", result.stdout)
            self.assertIn("file=test/rootfs-x86_64.img,", result.stdout)
            self.assertIn("target/x86_64-unknown-none/debug/bzImage", result.stdout)
            self.assertIn("init=/bin/sh", result.stdout)
            self.assertIn("-snapshot\n", result.stdout)

    def test_x86_rootfs_does_not_build_riscv_userspace(self):
        result = subprocess.run(
            ["make", "-n", "PLATFORM=x86_64", "rootfs"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertNotIn("./userspace/build", result.stdout)
        self.assertNotIn("./scripts/extract-probes.sh", result.stdout)
        self.assertIn("build-mrsh.sh", result.stdout)
        self.assertIn("build-toybox.sh", result.stdout)

    def test_riscv_rootfs_keeps_existing_userspace(self):
        result = subprocess.run(
            ["make", "-n", "PLATFORM=riscv64", "rootfs"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn("./userspace/build", result.stdout)
        self.assertIn("./scripts/extract-probes.sh", result.stdout)

    def test_userland_flags_follow_platform(self):
        for platform, compiler in [
            ("x86_64", "x86_64-linux-gnu-gcc"),
            ("riscv64", "riscv64-linux-gnu-gcc"),
        ]:
            with self.subTest(platform=platform):
                result = subprocess.run(
                    ["bash", "-c",
                     'source userspace/build-env.sh; printf "%s\\n" "$CC" "$MUSL_DIR" "$MUSL_CFLAGS"'],
                    cwd=ROOT, env=dict(os.environ, PLATFORM=platform),
                    text=True, capture_output=True, check=True,
                )
                self.assertEqual(result.stdout.splitlines()[0], compiler)
                self.assertIn(f"/{platform}-rux-linux-musl", result.stdout)
                self.assertEqual("-march=rv64gc_zicsr" in result.stdout, platform == "riscv64")


if __name__ == "__main__":
    unittest.main()
