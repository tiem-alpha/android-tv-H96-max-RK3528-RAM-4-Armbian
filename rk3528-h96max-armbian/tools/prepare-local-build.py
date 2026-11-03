#!/usr/bin/env python3
"""Prepare the existing Armbian snapshot without requiring its Git metadata."""
import hashlib
from pathlib import Path
import sys


def prepare(build):
    required = ["compile.sh", "lib/single.sh", "lib/functions", "config/boards/hinlink-ht2.csc",
                "config/sources/families/rk35xx.conf", "extensions", "packages", "patch", "tools"]
    missing = [name for name in required if not (build / name).exists()]
    if missing:
        raise SystemExit("Incomplete local Armbian tree: " + ", ".join(missing))
    # Docker calls this header unconditionally, even for a source archive.
    # Keep the adaptation here so it survives replacing the local build tree.
    log = build / "lib/functions/logging/export-logs.sh"
    text = log.read_text()
    marker = "\t# H96 local snapshot: no framework Git queries.\n"
    anchor = "function prepare_ansi_git_info_log_header() {\n"
    if marker not in text:
        if text.count(anchor) != 1:
            raise SystemExit("Unsupported Armbian logging layout; local snapshot adapter not applied")
        text = text.replace(anchor, anchor + marker +
            '\tif [[ ! -e "${SRC}/.git" ]]; then\n'
            '\t\tprintf "%s\\n" "Armbian local snapshot: ${BUILD_REPOSITORY_COMMIT:-unknown}"\n'
            '\t\treturn 0\n\tfi\n', 1)
        log.write_text(text)
    # Explicitly allow the cached build base when requested. Keep normal pull
    # behavior otherwise, and still pull if the image is absent.
    docker = build / "lib/functions/host/docker.sh"
    text = docker.read_text()
    old = 'if [[ "x${EXPIRED_MARKER}x" != "xx" ]]; then'
    new = 'if [[ "x${EXPIRED_MARKER}x" != "xx" && "${H96_DOCKER_LOCAL_BASE:-no}" != "yes" ]]; then'
    if old in text:
        text = text.replace(old, new, 1)
        docker.write_text(text)
    elif new not in text:
        raise SystemExit("Unsupported Docker base cache layout")
    # Hash only build inputs, excluding caches, outputs and metadata itself.
    digest = hashlib.sha256()
    inputs = [build / "compile.sh"]
    for name in ["lib", "config", "extensions", "packages", "patch", "tools", "vendor", "userpatches"]:
        inputs.extend(p for p in (build / name).rglob("*") if p.is_file())
    for path in sorted(inputs):
        if "__pycache__" in path.parts or path == build / "config/h96-local-build.conf":
            continue
        digest.update(path.relative_to(build).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    revision = "local-sha256-" + digest.hexdigest()
    (build / "config/h96-local-build.conf").write_text(
        "BUILD_REPOSITORY_URL=local-source-snapshot\n"
        f"BUILD_REPOSITORY_COMMIT={revision}\n")
    print(revision)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]).resolve())
