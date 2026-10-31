"""Bounded ZIP import/export for locally owned project snapshots."""
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from secrets import token_hex

FORMAT = 'chaos-project-v1'
MAX_ARCHIVE = 100 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024
MAX_FILE = 100 * 1024 * 1024
MAX_FILES = 2000


def inside(path, root):
    return path == root or root in path.parents


def safe_member(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name or name.startswith('/'):
        raise ValueError('archive contains an unsafe path')
    stripped = name.rstrip('/')
    parts = PurePosixPath(stripped).parts
    if (not parts or len(parts) > 20 or any(part in ('', '.', '..') or ':' in part or len(part) > 255
                                              for part in parts) or len(stripped) > 1024):
        raise ValueError('archive contains an unsafe path')
    if stripped != '/'.join(parts):
        raise ValueError('archive path is not canonical')
    return parts


class PortableProjects:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, exist_ok=True)

    def path(self, identifier):
        from job_service import SLUG
        if not isinstance(identifier, str) or not SLUG.fullmatch(identifier):
            raise ValueError('invalid project id')
        path = self.directory / identifier
        if path.is_symlink() or not path.is_dir():
            raise ValueError('project not found')
        return path

    def get(self, identifier):
        path = self.path(identifier)
        return json.loads((path / 'project.json').read_text())

    def list(self):
        result = []
        for path in sorted(self.directory.iterdir()):
            if not path.is_dir() or path.is_symlink() or path.name.startswith('.'):
                continue
            try:
                data = json.loads((path / 'project.json').read_text())
                result.append({key: data[key] for key in ('id', 'name', 'file_count', 'expanded_bytes', 'config_ids')})
            except (OSError, ValueError, KeyError):
                continue
        return result

    def _write_meta(self, path, metadata):
        temporary = path / ('.meta-' + token_hex(5))
        try:
            with temporary.open('x') as handle:
                os.chmod(temporary, 0o600)
                json.dump(metadata, handle, indent=2, ensure_ascii=False)
                handle.write('\n')
            temporary.replace(path / 'project.json')
        finally:
            temporary.unlink(missing_ok=True)

    def _extract(self, archive, destination):
        files = []
        seen = set()
        total = 0
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_FILES:
                raise ValueError('archive has too many entries')
            for info in members:
                parts = safe_member(info.filename)
                normalized = '/'.join(parts)
                folded = normalized.casefold()
                if folded in seen:
                    raise ValueError('archive has duplicate or case-colliding paths')
                seen.add(folded)
                mode = stat.S_IFMT(info.external_attr >> 16)
                if info.flag_bits & 1 or mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError('encrypted, linked or special archive entry refused')
                if info.is_dir():
                    (destination / normalized).mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                if info.file_size > MAX_FILE or info.compress_size > MAX_ARCHIVE:
                    raise ValueError('archive file exceeds size limit')
                total += info.file_size
                if total > MAX_EXPANDED:
                    raise ValueError('expanded archive exceeds size limit')
                if info.compress_size and info.file_size > max(1_048_576, 200 * info.compress_size):
                    raise ValueError('archive entry expands too aggressively')
                target = destination / normalized
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                actual = 0
                with bundle.open(info) as source, target.open('xb') as output:
                    os.chmod(target, 0o600)
                    while chunk := source.read(65536):
                        actual += len(chunk)
                        if actual > info.file_size or actual > MAX_FILE:
                            raise ValueError('archive entry exceeded declared size')
                        hasher.update(chunk)
                        output.write(chunk)
                if actual != info.file_size:
                    raise ValueError('archive entry size mismatch')
                if (info.external_attr >> 16) & 0o111:
                    target.chmod(0o700)
                files.append({'path': normalized, 'bytes': actual, 'sha256': hasher.hexdigest()})
        return files, total

    def _manifest_configs(self, files_root, manifest):
        if manifest.get('format') != FORMAT:
            raise ValueError('unsupported project manifest format')
        if 'config' in manifest and 'configs' in manifest:
            raise ValueError('manifest may not contain both config and configs')
        raws = manifest.get('configs', [manifest['config']] if 'config' in manifest else [])
        if not isinstance(raws, list) or len(raws) > 20:
            raise ValueError('manifest configs must be an array of at most 20')
        return [self._manifest_config(files_root, raw) for raw in raws]

    def _manifest_config(self, files_root, raw):
        if not isinstance(raw, dict):
            raise ValueError('each manifest config must be an object')
        config = dict(raw)
        if not isinstance(config.get('cwd', '.'), str):
            raise ValueError('manifest cwd must be a relative path')
        cwd = (files_root / config.get('cwd', '.')).resolve()
        if not inside(cwd, files_root.resolve()):
            raise ValueError('manifest cwd escapes imported project')
        sources = config.get('source_paths', [])
        if not isinstance(sources, list) or any(not isinstance(item, str) for item in sources):
            raise ValueError('manifest source_paths must be relative paths')
        resolved = []
        for source in sources:
            path = (files_root / source).resolve()
            if not inside(path, files_root.resolve()):
                raise ValueError('manifest source path escapes imported project')
            resolved.append(str(path))
        config['cwd'] = str(cwd)
        config['source_paths'] = resolved
        for key in ('target_command', 'checker_command'):
            command = config.get(key, [])
            if not isinstance(command, list) or any(not isinstance(arg, str) for arg in command):
                raise ValueError('manifest command must be an argument array')
            for arg in command[1:]:
                if isinstance(arg, str) and Path(arg).is_absolute() and not inside(Path(arg).resolve(), files_root.resolve()):
                    raise ValueError('manifest command references a file outside imported project')
        return config

    def import_zip(self, archive, identifier, name):
        from job_service import SLUG
        if not isinstance(identifier, str) or not SLUG.fullmatch(identifier):
            raise ValueError('project id must start with a letter and use letters, numbers, - or _')
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise ValueError('project name must have length 1..100')
        final = self.directory / identifier
        if final.exists() or final.is_symlink():
            raise ValueError('project id already exists')
        stage = self.directory / ('.stage-' + token_hex(8))
        stage.mkdir(mode=0o700)
        try:
            files_root = stage / 'files'
            files_root.mkdir(mode=0o700)
            files, total = self._extract(archive, files_root)
            manifest_path = files_root / 'chaos-project.json'
            if manifest_path.is_file() and manifest_path.stat().st_size > 65536:
                raise ValueError('manifest exceeds 64 KiB')
            manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {'format': FORMAT}
            if not isinstance(manifest, dict):
                raise ValueError('manifest must be a JSON object')
            configs = self._manifest_configs(files_root, manifest)
            metadata = {'id': identifier, 'name': name, 'file_count': len(files),
                        'expanded_bytes': total, 'config_ids': [], 'files': files}
            self._write_meta(stage, metadata)
            stage.rename(final)
            # Paths validated in the staging tree must now point to the final tree.
            old = str(files_root)
            new = str(final / 'files')
            for config in configs:
                config['cwd'] = new + config['cwd'][len(old):]
                config['source_paths'] = [new + path[len(old):] for path in config['source_paths']]
                for key in ('target_command', 'checker_command'):
                    config[key] = [new + arg[len(old):] if isinstance(arg, str) and arg.startswith(old + os.sep)
                                   else arg for arg in config.get(key, [])]
            return metadata, configs
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise

    def attach_config(self, identifier, config_id):
        path = self.path(identifier)
        metadata = self.get(identifier)
        if config_id not in metadata['config_ids']:
            metadata['config_ids'].append(config_id)
            self._write_meta(path, metadata)

    def config_for_export(self, identifier, config):
        base = (self.path(identifier) / 'files').resolve()
        cwd = Path(config['cwd']).resolve()
        if not inside(cwd, base):
            raise ValueError('config working directory is outside imported project')
        portable = dict(config)
        portable['cwd'] = str(cwd.relative_to(base)) or '.'
        paths = []
        for source in config['source_paths']:
            path = Path(source).resolve()
            if not inside(path, base):
                raise ValueError('config source file is outside imported project')
            paths.append(str(path.relative_to(base)))
        portable['source_paths'] = paths
        for key in ('target_command', 'checker_command'):
            changed = []
            for arg in portable[key]:
                if str(base) in arg:
                    path = Path(arg).resolve()
                    if not inside(path, base):
                        raise ValueError('command embeds an unportable path')
                    changed.append(os.path.relpath(path, cwd))
                else:
                    changed.append(arg)
            portable[key] = changed
        return portable

    def export_zip(self, identifier, configs=None):
        path = self.path(identifier)
        files_root = path / 'files'
        metadata = self.get(identifier)
        temporary = tempfile.NamedTemporaryFile(prefix='chaos-export-', suffix='.zip', delete=False)
        export_path = Path(temporary.name)
        temporary.close()
        try:
            with zipfile.ZipFile(export_path, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
                count = 0
                for record in metadata['files']:
                    if record['path'] == 'chaos-project.json':
                        continue
                    file = files_root / record['path']
                    if file.is_symlink() or not file.is_file() or not inside(file.resolve(), files_root.resolve()):
                        raise ValueError('imported source is missing or linked; export refused')
                    hasher = hashlib.sha256()
                    with file.open('rb') as source:
                        while chunk := source.read(65536):
                            hasher.update(chunk)
                    if hasher.hexdigest() != record['sha256']:
                        raise ValueError('imported source changed; export refused')
                    bundle.write(file, record['path'])
                    count += 1
                    if count > MAX_FILES or export_path.stat().st_size > MAX_ARCHIVE:
                        raise ValueError('export exceeds size limit')
                manifest = {'format': FORMAT}
                portable_configs = [self.config_for_export(identifier, config) for config in (configs or [])]
                if len(portable_configs) == 1:
                    manifest['config'] = portable_configs[0]
                elif portable_configs:
                    manifest['configs'] = portable_configs
                manifest_bytes = (json.dumps(manifest, indent=2) + '\n').encode()
                if len(manifest_bytes) > 65536:
                    raise ValueError('portable manifest exceeds 64 KiB')
                bundle.writestr('chaos-project.json', manifest_bytes)
            if export_path.stat().st_size > MAX_ARCHIVE:
                raise ValueError('export exceeds size limit')
            return export_path
        except Exception:
            export_path.unlink(missing_ok=True)
            raise
