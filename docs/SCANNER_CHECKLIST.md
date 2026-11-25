# Scanner and printer-scanner checklist (G3 / G11)

The app scans; it does not print (printing and marking papers is out of scope, SPEC section 3). It can take pages from:

| Path | Covers | How the app reaches it |
|---|---|---|
| **WIA** (Windows) | Any scanner or printer-scanner with a Windows driver, USB or network (HP, Canon, Epson, Brother, Xerox, Ricoh, Kyocera, Lexmark, Fujitsu, Plustek...) | `WiaScanner`, PowerShell COM, no extra install |
| **eSCL / AirScan / Mopria** | Network printer-scanners from about 2015 on, with no driver needed, on any OS | `EsclScanner`: found automatically on the local network (mDNS), or added by IP address |
| **SANE** (Linux/BSD) | Everything SANE supports (thousands of models) | `SaneScanner` (`scanimage`) |
| **Watch folder** | Anything else: TWAIN-only or vendor-locked devices, the printer's own scan-to-folder or scan-to-network-share, a phone scanner app saving to a synced folder | `FolderWatcher` |
| **Upload** | Image or PDF files from anywhere | Scan screen, Upload files |

Automated coverage: WIA device listing runs on this machine (no WIA device was attached on 2026-11-25). The eSCL protocol is tested end to end over real HTTP against a mock printer: feeder, glass, busy, empty-feeder, unreachable address. SANE device parsing has a unit test. Folder watching and upload have tests in G3. **None of this has run against real hardware yet.** That is what this checklist is for.

## With the real printer-scanner

Run each line that applies to the device, and record the model and result at the bottom.

**Finding the device (Scan screen)**
- [ ] The scanner appears in the Scanner list within about 3 seconds, labelled "USB or installed" (WIA) or "Network" (eSCL).
- [ ] Network printer not listed: type its IP address (printer panel > Network settings) and press **Add**; it is added with its model name.
- [ ] Scanner switched off: **Find scanners** no longer lists it, and starting a scan shows "No scanner found" or "could not reach the printer" in red on the batch. Nothing crashes.

**Scanning**
- [ ] Feeder: load 3 papers, page 1 first, press **Start scanning**: every page arrives in order, and Pages goes up by one per sheet.
- [ ] Glass: one page on the glass, feeder empty: exactly one page arrives per press.
- [ ] The stored original (`data/batches/<id>/orig/000001.jpg`) is grayscale at about 150 dpi (about 1240x1754 for A4).
- [ ] Scanning the same sheet twice adds two pages (they are different scans). Re-uploading the same file adds none.
- [ ] Pause during a feeder run: pages already scanned are kept, and processing waits until Resume.

**Fallbacks**
- [ ] TWAIN-only or vendor-locked device: set its software to save into a folder, choose **Watch folder** with that folder, and the pages arrive within 5 s of each save.
- [ ] Printer's own "scan to network folder" or "scan to PC": point it at the watched folder and the same result follows.

## Results
| Date | Make / model | Connection (USB / network) | Path (WIA / eSCL / SANE / folder) | Pass / fail and notes |
|---|---|---|---|---|
| | | | | |
