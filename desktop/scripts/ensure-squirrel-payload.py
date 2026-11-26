"""Verify the Squirrel bootstrapper and repair unsigned builds missing their payload."""

import ctypes
import hashlib
import io
import mmap
import shutil
import sys
import tempfile
import zipfile
from ctypes import wintypes
from pathlib import Path


RESOURCE_TYPE = "DATA"
RESOURCE_ID = 131
LANGUAGE = 0x0409
LOAD_LIBRARY_AS_DATAFILE = 0x00000002

kernel = ctypes.WinDLL("kernel32", use_last_error=True)


def bind(name, result, *args):
    function = getattr(kernel, name)
    function.restype = result
    function.argtypes = args
    return function


load_library = bind("LoadLibraryExW", wintypes.HMODULE, wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
free_library = bind("FreeLibrary", wintypes.BOOL, wintypes.HMODULE)
find_resource = bind("FindResourceExW", wintypes.HRSRC, wintypes.HMODULE, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.WORD)
resource_size = bind("SizeofResource", wintypes.DWORD, wintypes.HMODULE, wintypes.HRSRC)
load_resource = bind("LoadResource", wintypes.HGLOBAL, wintypes.HMODULE, wintypes.HRSRC)
lock_resource = bind("LockResource", wintypes.LPVOID, wintypes.HGLOBAL)
begin_update = bind("BeginUpdateResourceW", wintypes.HANDLE, wintypes.LPCWSTR, wintypes.BOOL)
update_resource = bind(
    "UpdateResourceW", wintypes.BOOL, wintypes.HANDLE, wintypes.LPCWSTR,
    wintypes.LPVOID, wintypes.WORD, wintypes.LPVOID, wintypes.DWORD,
)
end_update = bind("EndUpdateResourceW", wintypes.BOOL, wintypes.HANDLE, wintypes.BOOL)


def contains_release(installer, package_name, package_size, package_hash):
    module = load_library(str(installer), None, LOAD_LIBRARY_AS_DATAFILE)
    if not module:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        resource = find_resource(module, RESOURCE_TYPE, RESOURCE_ID, LANGUAGE)
        if not resource:
            return False
        data = lock_resource(load_resource(module, resource))
        if not data:
            return False
        try:
            payload = ctypes.string_at(data, resource_size(module, resource))
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if archive.getinfo("Update.exe").file_size == 0:
                    return False
                if archive.getinfo(package_name).file_size != package_size:
                    return False
                entry = archive.read("RELEASES").decode("utf-8-sig").split()
                if entry != [package_hash.upper(), package_name, str(package_size)]:
                    return False
                with archive.open(package_name) as package:
                    return hashlib.file_digest(package, "sha1").hexdigest() == package_hash
        except (KeyError, zipfile.BadZipFile, UnicodeDecodeError):
            return False
    finally:
        free_library(module)


def write_payload(installer, payload):
    with payload.open("r+b") as file, mmap.mmap(file.fileno(), 0) as data:
        pointer = ctypes.c_char.from_buffer(data)
        try:
            handle = begin_update(str(installer), False)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            if not update_resource(handle, RESOURCE_TYPE, RESOURCE_ID, LANGUAGE, ctypes.addressof(pointer), len(data)):
                error = ctypes.get_last_error()
                end_update(handle, True)
                raise ctypes.WinError(error)
            if not end_update(handle, False):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            del pointer


def ensure_payload(installer, package, installer_tools):
    with package.open("rb") as file:
        package_hash = hashlib.file_digest(file, "sha1").hexdigest()
    package_size = package.stat().st_size
    if contains_release(installer, package.name, package_size, package_hash):
        return

    # Squirrel can report success after its bundled resource writer fails.
    # Repair a temporary copy, then replace the stub only after verifying it.
    release = f"{package_hash.upper()} {package.name} {package_size}\n"
    with tempfile.TemporaryDirectory(prefix="squirrel-", dir=installer.parent) as directory:
        payload = Path(directory) / "payload.zip"
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(package, package.name)
            archive.write(installer_tools / "vendor" / "Squirrel.exe", "Update.exe")
            archive.write(installer_tools / "resources" / "install-spinner.gif", "background.gif")
            archive.writestr("RELEASES", release)
        repaired = Path(directory) / installer.name
        shutil.copyfile(installer, repaired)
        write_payload(repaired, payload)
        if not contains_release(repaired, package.name, package_size, package_hash):
            raise RuntimeError("The repaired Squirrel installer still has no valid package payload.")
        repaired.replace(installer)
        print(f"Repaired and verified the embedded package in {installer.name}.")


if __name__ == "__main__":
    ensure_payload(*(Path(value).resolve() for value in sys.argv[1:]))
