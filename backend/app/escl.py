"""eSCL (Apple AirScan / Mopria) driverless network scanning, plus mDNS discovery.
Most network printer-scanners sold since about 2015 (HP, Canon, Epson, Brother, Xerox, Ricoh, Kyocera, Lexmark...)
speak it, on Windows, macOS and Linux, with no driver installed."""
import time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import httpx

NS = {"scan": "http://schemas.hp.com/imaging/escl/2011/05/03", "pwg": "http://www.pwg.org/schemas/2010/12/sm"}
A4 = (2480, 3508)  # 1/300 inch
SETTINGS = """<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03" xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
  <pwg:Version>2.0</pwg:Version>
  <pwg:ScanRegions><pwg:ScanRegion>
    <pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>
    <pwg:XOffset>0</pwg:XOffset><pwg:YOffset>0</pwg:YOffset>
    <pwg:Width>{w}</pwg:Width><pwg:Height>{h}</pwg:Height>
  </pwg:ScanRegion></pwg:ScanRegions>
  <pwg:InputSource>{source}</pwg:InputSource>
  <scan:ColorMode>Grayscale8</scan:ColorMode>
  <scan:XResolution>150</scan:XResolution><scan:YResolution>150</scan:YResolution>
  <pwg:DocumentFormat>image/jpeg</pwg:DocumentFormat>
  <scan:DocumentFormatExt>image/jpeg</scan:DocumentFormatExt>
</scan:ScanSettings>"""


class ScannerError(RuntimeError):
    pass


def normalize_url(address: str) -> str:
    """'192.168.1.20' or 'http://host:8080/eSCL/' -> 'http://192.168.1.20/eSCL'. Only http(s)."""
    a = address.strip()
    if "://" not in a:
        a = "http://" + a
    u = urlparse(a)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ScannerError(f"not a printer address: {address}")
    path = u.path.rstrip("/") or "/eSCL"
    return f"{u.scheme}://{u.netloc}{path}"


class EsclScanner:
    def __init__(self, address: str, client: httpx.Client | None = None):
        self.url = normalize_url(address)
        # Printers ship self-signed certificates, so https eSCL cannot be verified; it only ever talks to the LAN
        # address the teacher picked, and nothing but scan settings is sent.
        self.http = client or httpx.Client(timeout=60, verify=False)

    def _call(self, method, url, **kw):
        try:
            return self.http.request(method, url, **kw)
        except httpx.HTTPError as e:
            raise ScannerError(f"could not reach the printer at {self.url} ({type(e).__name__})") from None

    def _get(self, path):
        r = self._call("GET", f"{self.url}/{path}")
        if r.status_code != 200:
            raise ScannerError(f"{path}: HTTP {r.status_code}")
        return ET.fromstring(r.content)

    def capabilities(self) -> dict:
        try:
            root = self._get("ScannerCapabilities")
        except ET.ParseError:
            raise ScannerError(f"the device at {self.url} is not an eSCL scanner") from None
        name = root.findtext("pwg:MakeAndModel", default="", namespaces=NS) or self.url
        sources = {}
        for tag, src in (("scan:Platen", "Platen"), ("scan:Adf", "Feeder")):
            el = root.find(f".//{tag}", NS)
            if el is not None:
                w = int(el.findtext(".//scan:MaxWidth", default=str(A4[0]), namespaces=NS))
                h = int(el.findtext(".//scan:MaxHeight", default=str(A4[1]), namespaces=NS))
                sources[src] = (min(w, A4[0]), min(h, A4[1]))
        if not sources:
            raise ScannerError("the printer reports no scan source")
        return {"name": name, "sources": sources}

    def feeder_loaded(self) -> bool:
        try:
            return self._get("ScannerStatus").findtext(".//scan:AdfState", default="", namespaces=NS) == "ScannerAdfLoaded"
        except ScannerError:
            return False

    def scan(self, source: str | None = None, busy_wait=1.0, busy_tries=60):
        """Yield (name, jpeg bytes): the whole feeder if paper is loaded there, else one page from the glass."""
        caps = self.capabilities()
        if source is None:
            source = "Feeder" if "Feeder" in caps["sources"] and self.feeder_loaded() else next(iter(caps["sources"]))
        w, h = caps["sources"][source]
        r = self._call("POST", f"{self.url}/ScanJobs", content=SETTINGS.format(w=w, h=h, source=source),
                       headers={"content-type": "text/xml"})
        if r.status_code not in (200, 201) or "location" not in r.headers:
            raise ScannerError(f"printer refused the scan job: HTTP {r.status_code}")
        job = urljoin(self.url + "/", r.headers["location"]).rstrip("/")
        n = tries = 0
        while True:
            d = self._call("GET", f"{job}/NextDocument")
            if d.status_code == 200:
                n += 1
                yield f"escl_{n:05d}.jpg", d.content
                if source == "Platen":
                    return
            elif d.status_code == 404:  # feeder empty: job done
                return
            elif d.status_code == 503 and tries < busy_tries:  # warming up / busy
                tries += 1
                time.sleep(busy_wait)
            else:
                raise ScannerError(f"scan stopped: HTTP {d.status_code}")


def discover(timeout=2.0) -> list[dict]:
    """eSCL printers announced on the local network (mDNS _uscan / _uscans)."""
    from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf
    found = {}

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name, timeout=1500)
            addrs = info.parsed_addresses(IPVersion.V4Only) if info else []
            if not addrs:
                return
            props = {k.decode(): (v or b"").decode(errors="ignore") for k, v in info.properties.items()}
            scheme = "https" if type_.startswith("_uscans") else "http"
            url = f"{scheme}://{addrs[0]}:{info.port}/{props.get('rs', 'eSCL').strip('/')}"
            if addrs[0] not in found or scheme == "http":  # prefer plain http: printer certificates are self-signed
                found[addrs[0]] = {"kind": "escl", "id": url, "name": props.get("ty") or name.split(".")[0]}

        def update_service(self, *a):
            pass

        def remove_service(self, *a):
            pass

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, ["_uscan._tcp.local.", "_uscans._tcp.local."], Listener())
        time.sleep(timeout)
    finally:
        zc.close()
    return list(found.values())
