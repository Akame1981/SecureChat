"""utils/auto_updater.py

Simple auto-updater that periodically checks a GitHub repo branch for a
new commit SHA and downloads the zipball into an "updates" directory when
an update is detected.

This implementation is intentionally conservative: it downloads and
extracts the repo archive to updates/<sha>/ and notifies the GUI. It does
not automatically overwrite running files or restart the application.
The user is notified to restart the app to install the update.

Defaults use the current repository owner/name (Akame1981/Whispr) and
branch 'main'. The check interval is configurable by the caller.
"""
import os
import time
import json
import threading
import tempfile
import shutil
import zipfile
from typing import Optional

import requests


UPDATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "updates"))


def _ensure_updates_dir():
    try:
        os.makedirs(UPDATES_DIR, exist_ok=True)
    except Exception:
        pass


def _last_seen_file(owner: str, repo: str, branch: str) -> str:
    name = f"last_seen_{owner}_{repo}_{branch}.json"
    return os.path.join(UPDATES_DIR, name)


def get_latest_commit_sha(owner: str, repo: str, branch: str = "main") -> Optional[str]:
    """Return latest commit sha for given repo/branch or None on error."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            # Could be rate-limited or branch missing
            return None
        data = resp.json()
        return data.get("sha")
    except Exception:
        return None


def _read_last_seen(owner: str, repo: str, branch: str) -> Optional[str]:
    path = _last_seen_file(owner, repo, branch)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("sha")
    except Exception:
        return None


def _write_last_seen(owner: str, repo: str, branch: str, sha: str):
    path = _last_seen_file(owner, repo, branch)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"sha": sha}, f)
    except Exception:
        pass


def download_and_extract_zip(owner: str, repo: str, branch: str, sha: str) -> Optional[str]:
    """Download the branch zipball and extract into updates/<sha>.

    Returns the extraction path on success or None on failure.
    """
    _ensure_updates_dir()
    zip_name = f"{repo}-{branch}-{sha}.zip"
    zip_path = os.path.join(UPDATES_DIR, zip_name)
    extract_dir = os.path.join(UPDATES_DIR, sha)

    # If already extracted, return immediately
    if os.path.isdir(extract_dir):
        return extract_dir

    try:
        url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        with requests.get(url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                return None
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        # Extract safely into a temp dir then move
        tmpdir = tempfile.mkdtemp(prefix="whispr_update_")
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            # The zip usually creates a top-level folder like repo-branch
            # Move its contents into extract_dir
            members = os.listdir(tmpdir)
            if len(members) == 1:
                src = os.path.join(tmpdir, members[0])
            else:
                src = tmpdir

            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            shutil.move(src, extract_dir)
            return extract_dir
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        # Leave zip as-is for debugging and return None
        return None


def check_and_download(app, owner: str, repo: str, branch: str = "main") -> bool:
    """Check GitHub for new commit and download update.

    If an update is downloaded, the function notifies the GUI via
    app.notifier.show(...) when available. Returns True if an update was
    downloaded, False otherwise.
    """
    try:
        latest = get_latest_commit_sha(owner, repo, branch)
        if not latest:
            return False

        last = _read_last_seen(owner, repo, branch)
        if last == latest:
            return False

        # Download and extract
        extracted = download_and_extract_zip(owner, repo, branch, latest)
        if extracted:
            _write_last_seen(owner, repo, branch, latest)
            msg = f"Update downloaded ({latest[:7]}). Restart app to apply."
            print("[auto_updater] ", msg)
            try:
                if hasattr(app, "notifier") and app.notifier:
                    app.notifier.show(msg, type_="info")
                elif hasattr(app, "after"):
                    # Schedule a simple popup using Tk if available
                    def _n():
                        try:
                            import tkinter as tk
                            tk.messagebox.showinfo("Whispr", msg)
                        except Exception:
                            print(msg)
                    try:
                        app.after(0, _n)
                    except Exception:
                        print(msg)
            except Exception:
                print(msg)
            return True
    except Exception as e:
        print(f"[auto_updater] failed: {e}")
    return False


def start_auto_update_loop(app, owner: str, repo: str, branch: str, interval: float):
    """Background loop to periodically check for updates until app.stop_event set."""
    _ensure_updates_dir()
    while not getattr(app, "stop_event", threading.Event()).is_set():
        try:
            try:
                check_and_download(app, owner, repo, branch)
            except Exception:
                pass
            # Sleep in small chunks so stop_event can break quickly
            slept = 0.0
            while slept < interval and not getattr(app, "stop_event", threading.Event()).is_set():
                time.sleep(0.5)
                slept += 0.5
        except Exception:
            # On unexpected error, wait some time before retrying
            time.sleep(10)


def run_auto_update_check_in_thread(app, owner: str = "Akame1981", repo: str = "Whispr", branch: str = "main", interval: float = 3600.0):
    """Start the auto-update loop in a daemon thread.

    interval is in seconds. Default 1 hour.
    """
    t = threading.Thread(target=start_auto_update_loop, args=(app, owner, repo, branch, interval), daemon=True)
    t.start()
    return t


# ------------------ Apply-on-next-start helpers ------------------


def _pending_file_path() -> str:
    _ensure_updates_dir()
    return os.path.join(UPDATES_DIR, "pending_update.json")


def mark_update_for_apply(sha: str) -> bool:
    """Mark a downloaded update (sha) to be applied on next start.

    This writes a small JSON file under updates/ indicating which sha to
    apply. Returns True on success.
    """
    try:
        _ensure_updates_dir()
        with open(_pending_file_path(), "w", encoding="utf-8") as f:
            json.dump({"sha": sha}, f)
        return True
    except Exception:
        return False


def get_pending_update() -> Optional[str]:
    """Return pending sha if any, else None."""
    path = _pending_file_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("sha")
    except Exception:
        return None


def clear_pending_update():
    try:
        p = _pending_file_path()
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


def _should_exclude(relpath: str, exclude_dirs=None):
    if not exclude_dirs:
        exclude_dirs = {"venv", ".git", "updates", "data", "node_modules"}
    parts = relpath.replace("\\", "/").split("/")
    return any(p in exclude_dirs for p in parts)


def apply_update(sha: str, project_root: Optional[str] = None, make_backup: bool = True) -> bool:
    """Apply the extracted update identified by sha into project_root.

    Steps:
    - Locate extracted update at updates/<sha>/
    - Create a backup of project_root files under updates/backups/<timestamp>/
    - Copy update files into project_root (overwriting existing files), skipping
      configured excluded paths.

    Returns True on success, False on failure. This is a best-effort helper
    and does not attempt complex rollback for partial failures (but backup
    is created so manual rollback is possible).
    """
    if not sha:
        return False

    if project_root is None:
        # Default to repo root (one level above this utils package)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    extracted_dir = os.path.join(UPDATES_DIR, sha)
    if not os.path.isdir(extracted_dir):
        print(f"[auto_updater] extracted update not found: {extracted_dir}")
        return False

    # Backup current project
    backup_path = None
    if make_backup:
        try:
            ts = int(time.time())
            backups_root = os.path.join(UPDATES_DIR, "backups")
            os.makedirs(backups_root, exist_ok=True)
            backup_path = os.path.join(backups_root, f"backup_{ts}")
            shutil.copytree(project_root, backup_path, dirs_exist_ok=False, ignore=shutil.ignore_patterns('venv', '.git', 'updates', '__pycache__', 'node_modules', 'data'))
        except Exception as e:
            print(f"[auto_updater] backup failed: {e}")
            # Continue, but warn
            backup_path = None

    # Copy files from extracted_dir into project_root
    try:
        # The extracted tree may have a top-level folder like repo-branch; handle both cases
        entries = os.listdir(extracted_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(extracted_dir, entries[0])):
            src_root = os.path.join(extracted_dir, entries[0])
        else:
            src_root = extracted_dir

        for root, dirs, files in os.walk(src_root):
            rel = os.path.relpath(root, src_root)
            if rel == ".":
                rel = ""
            if _should_exclude(rel):
                # Skip entire subtree
                dirs[:] = []
                continue

            # Ensure target directory exists
            target_dir = os.path.join(project_root, rel) if rel else project_root
            os.makedirs(target_dir, exist_ok=True)

            for fname in files:
                src_file = os.path.join(root, fname)
                rel_file = os.path.join(rel, fname) if rel else fname
                if _should_exclude(rel_file):
                    continue
                target_file = os.path.join(project_root, rel_file)
                try:
                    # Ensure parent dir exists (already created above but just in case)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    shutil.copy2(src_file, target_file)
                except Exception as e:
                    print(f"[auto_updater] failed copying {src_file} -> {target_file}: {e}")
                    # Continue copying other files
                    continue

        # If we reach here, update applied (best-effort)
        print(f"[auto_updater] update {sha} applied to {project_root}")
        # Clear pending marker if any
        try:
            pending = get_pending_update()
            if pending == sha:
                clear_pending_update()
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[auto_updater] apply failed: {e}")
        return False


def apply_pending_update(project_root: Optional[str] = None) -> bool:
    """If a pending update is marked, attempt to apply it.

    Returns True if an update was applied, False otherwise.
    """
    sha = get_pending_update()
    if not sha:
        return False
    return apply_update(sha, project_root=project_root)

