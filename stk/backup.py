import hashlib
import json
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


class BackupError(RuntimeError):
    pass


def _sqlite_path(database_url):
    if not database_url.startswith("sqlite+"):
        return None
    return Path(urlparse(database_url.replace("sqlite+aiosqlite", "sqlite", 1)).path)


def _digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def create_backup(database_url, instance_path, output):
    instance_path, output = Path(instance_path), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        root = Path(temporary)
        sqlite_path = _sqlite_path(database_url)
        if sqlite_path:
            database_name = "database.sqlite3"
            with (
                sqlite3.connect(sqlite_path) as source,
                sqlite3.connect(root / database_name) as target,
            ):
                source.backup(target)
            kind = "sqlite"
        else:
            database_name, kind = "database.dump", "postgresql"
            try:
                subprocess.run(
                    [
                        "pg_dump",
                        "--format=custom",
                        "--file",
                        str(root / database_name),
                        database_url,
                    ],
                    check=True,
                )
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise BackupError(f"PostgreSQL backup failed: {exc}") from exc
        invoices = instance_path / "invoices"
        if invoices.exists():
            shutil.copytree(invoices, root / "invoices")
        files = {}
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            relative = path.relative_to(root).as_posix()
            files[relative] = {"sha256": _digest(path), "size": path.stat().st_size}
        manifest = {
            "format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "database": {"kind": kind, "file": database_name},
            "files": files,
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        pending = output.with_suffix(output.suffix + ".tmp")
        with tarfile.open(pending, "w:gz") as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(root))
        pending.replace(output)
    return output


def _extract_verified(archive, target):
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)):
                raise BackupError("Backup contains duplicate members")
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not member.isfile():
                    raise BackupError("Backup contains an unsafe member")
            bundle.extractall(target, filter="data")
    except (tarfile.TarError, OSError) as exc:
        raise BackupError(f"Invalid backup archive: {exc}") from exc
    manifest_path = target / "manifest.json"
    if not manifest_path.is_file():
        raise BackupError("Backup manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise BackupError("Unsupported backup format")
    for name, expected in manifest.get("files", {}).items():
        path = target / name
        if not path.is_file() or _digest(path) != expected["sha256"]:
            raise BackupError(f"Backup checksum failed for {name}")
    return manifest


def verify_backup(archive):
    with tempfile.TemporaryDirectory() as temporary:
        return _extract_verified(Path(archive), Path(temporary))


def restore_backup(archive, database_url, instance_path, *, force=False):
    instance_path = Path(instance_path)
    sqlite_path = _sqlite_path(database_url)
    invoices = instance_path / "invoices"
    occupied = (sqlite_path and sqlite_path.exists()) or (
        invoices.exists() and any(invoices.rglob("*"))
    )
    if occupied and not force:
        raise BackupError("Restore target is not empty")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = _extract_verified(Path(archive), root)
        if force:
            safety = (
                instance_path / f"restore-safety-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
            )
            safety.mkdir(parents=True, exist_ok=False)
            if sqlite_path and sqlite_path.exists():
                shutil.copy2(sqlite_path, safety / sqlite_path.name)
            if invoices.exists():
                shutil.move(invoices, safety / "invoices")
        database_file = root / manifest["database"]["file"]
        if manifest["database"]["kind"] == "sqlite":
            if sqlite_path is None:
                raise BackupError("Backup database type does not match target")
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(database_file, sqlite_path)
        else:
            try:
                subprocess.run(
                    [
                        "pg_restore",
                        "--clean",
                        "--if-exists",
                        "--dbname",
                        database_url,
                        str(database_file),
                    ],
                    check=True,
                )
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                raise BackupError(f"PostgreSQL restore failed: {exc}") from exc
        if (root / "invoices").exists():
            invoices.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(root / "invoices", invoices)
