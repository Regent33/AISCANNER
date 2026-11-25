"""Scanner adapters. Each yields (file name, bytes) pages; ingest() stores them untouched.

  WiaScanner   any scanner or printer-scanner with a Windows (WIA) driver, USB or network
  EsclScanner  driverless network scanning: eSCL / AirScan / Mopria (see escl.py), any OS
  SaneScanner  Linux / BSD scanners through SANE's `scanimage`
  MockScanner  images from a folder (tests, demos)

Anything else (TWAIN-only or vendor-locked devices, scan-to-folder or scan-to-email from the printer's panel):
the device's own software saves into a folder and FolderWatcher (ingest.py) picks the pages up.
"""
import os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import escl
from .escl import EsclScanner, ScannerError  # noqa: F401 (re-exported)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


class MockScanner:
    """Direct-trigger path without hardware: 'scans' the image files of a folder in name order."""

    def __init__(self, folder):
        self.folder = Path(folder)

    def scan(self):
        for f in sorted((p for p in self.folder.iterdir() if p.suffix.lower() in IMAGE_EXT), key=natural_key):
            yield f.name, f.read_bytes()


WIA_SCAN_PS = r"""
$ErrorActionPreference = 'Stop'
$out = $env:SCAN_OUT; $want = $env:SCAN_DEVICE   # passed as data, never spliced into the script
$dm = New-Object -ComObject WIA.DeviceManager
$info = $dm.DeviceInfos | Where-Object { $_.Type -eq 1 -and (-not $want -or $_.DeviceID -eq $want) } | Select-Object -First 1
if (-not $info) { Write-Error 'NO_SCANNER' }
$dev = $info.Connect()
$item = $dev.Items.Item(1)
function SetProp($props, $id, $val) { foreach ($p in $props) { if ($p.PropertyID -eq $id) { try { $p.Value = $val } catch {} } } }
SetProp $item.Properties 6146 2      # WIA_IPS_CUR_INTENT = grayscale
SetProp $item.Properties 6147 150    # horizontal dpi
SetProp $item.Properties 6148 150    # vertical dpi
$fmtJpeg = '{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}'
$n = 0
while ($true) {
  try { $img = $item.Transfer($fmtJpeg) } catch { if ($n -gt 0) { break } else { throw } }
  $n++
  $img.SaveFile((Join-Path $out ('wia_{0:D5}.jpg' -f $n)))
  # flatbed: one page per trigger; feeder: loop until WIA_ERROR_PAPER_EMPTY
  $handling = ($dev.Properties | Where-Object { $_.PropertyID -eq 3088 }).Value
  if (-not $handling -or ($handling -band 1) -eq 0) { break }
}
"""

WIA_LIST_PS = r"""
$dm = New-Object -ComObject WIA.DeviceManager
$dm.DeviceInfos | Where-Object { $_.Type -eq 1 } | ForEach-Object { $_.DeviceID + '|' + $_.Properties.Item('Name').Value }
"""


def _ps(script, timeout=600, env=None):
    """Run a fixed PowerShell script. Variable inputs go through env (never string formatting: PowerShell also
    treats curly quotes as quote characters, so escaping by hand is unsafe)."""
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})})


class WiaScanner:
    """Windows Image Acquisition via PowerShell COM (no pywin32). Hardware steps: docs/SCANNER_CHECKLIST.md."""

    def __init__(self, device_id: str | None = None):
        self.device_id = device_id or ""

    @staticmethod
    def list_devices() -> list[dict]:
        if sys.platform != "win32":
            return []
        r = _ps(WIA_LIST_PS, timeout=60)
        out = []
        for line in r.stdout.splitlines() if r.returncode == 0 else []:
            dev_id, _, name = line.strip().partition("|")
            if dev_id:
                out.append({"kind": "wia", "id": dev_id, "name": name or "Scanner"})
        return out

    def scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _ps(WIA_SCAN_PS, env={"SCAN_OUT": tmp, "SCAN_DEVICE": self.device_id})
            if r.returncode != 0:
                raise ScannerError("NO_SCANNER" if "NO_SCANNER" in r.stderr else r.stderr.strip()[-500:])
            for f in sorted(Path(tmp).iterdir(), key=natural_key):
                yield f.name, f.read_bytes()


SANE_LINE = re.compile(r"device `([^']+)' is a (.+)")


def parse_sane_list(text: str) -> list[dict]:
    return [{"kind": "sane", "id": m.group(1), "name": m.group(2).strip()} for m in map(SANE_LINE.search, text.splitlines()) if m]


class SaneScanner:
    """Linux / BSD: SANE's scanimage. Tries the document feeder first, then one page from the glass."""

    def __init__(self, device: str):
        self.device = device

    @staticmethod
    def list_devices() -> list[dict]:
        if not shutil.which("scanimage"):
            return []
        r = subprocess.run(["scanimage", "-L"], capture_output=True, text=True, timeout=60)
        return parse_sane_list(r.stdout)

    def scan(self):
        base = ["scanimage", "-d", self.device, "--format=png", "--mode", "Gray", "--resolution", "150"]
        with tempfile.TemporaryDirectory() as tmp:
            feeder = subprocess.run(base + ["--source", "ADF", f"--batch={tmp}/sane_%05d.png"], capture_output=True, timeout=1800)
            pages = sorted(Path(tmp).glob("sane_*.png"), key=natural_key)
            if feeder.returncode != 0 and not pages:
                flat = subprocess.run(base, capture_output=True, timeout=600)
                if flat.returncode != 0 or not flat.stdout:
                    raise ScannerError(flat.stderr.decode(errors="ignore").strip()[-500:] or "scan failed")
                yield "sane_00001.png", flat.stdout
                return
            for f in pages:
                yield f.name, f.read_bytes()


def discover() -> list[dict]:
    """Every scanner this computer can reach right now, from all backends at once (about 2-3 s)."""
    jobs = (WiaScanner.list_devices, escl.discover, SaneScanner.list_devices)
    with ThreadPoolExecutor(len(jobs)) as pool:
        results = [pool.submit(j) for j in jobs]
    found = []
    for r in results:
        try:
            found += r.result()
        except Exception:  # one backend failing (no zeroconf, no permission) never hides the others
            pass
    return found


def make(kind: str, target: str | None):
    if kind == "wia":
        return WiaScanner(target)
    if kind == "escl":
        if not target:
            raise ScannerError("which printer? give its address")
        return EsclScanner(target)
    if kind == "sane":
        if not target or target.startswith("-"):
            raise ScannerError("which scanner? pick one from the list")
        return SaneScanner(target)
    if kind == "mock":
        return MockScanner(target)
    raise ScannerError(f"unknown scanner type {kind}")
