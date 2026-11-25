"""A tiny eSCL (AirScan) printer on 127.0.0.1 for tests: capabilities, status, scan jobs, one busy reply, then pages
until the feeder is empty. Speaks the real HTTP protocol, so EsclScanner is exercised end to end."""
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image

CAPS = """<?xml version="1.0" encoding="UTF-8"?>
<scan:ScannerCapabilities xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03" xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
  <pwg:Version>2.63</pwg:Version><pwg:MakeAndModel>Mock Printer 3000</pwg:MakeAndModel>
  <scan:Platen><scan:PlatenInputCaps><scan:MaxWidth>2550</scan:MaxWidth><scan:MaxHeight>3508</scan:MaxHeight></scan:PlatenInputCaps></scan:Platen>
  <scan:Adf><scan:AdfSimplexInputCaps><scan:MaxWidth>2550</scan:MaxWidth><scan:MaxHeight>4200</scan:MaxHeight></scan:AdfSimplexInputCaps></scan:Adf>
</scan:ScannerCapabilities>"""


def page(i):
    im = Image.new("L", (124, 175), 255)
    im.putpixel((i % 124, i % 175), 0)
    b = io.BytesIO()
    im.save(b, "JPEG")
    return b.getvalue()


class MockPrinter:
    def __init__(self, pages=3):
        self.feeder = [page(i) for i in range(pages)]
        self.jobs, self.busy_once = [], True
        printer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, code, body=b"", ctype="text/xml", headers=()):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                for k, v in headers:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/eSCL/ScannerCapabilities":
                    return self.reply(200, CAPS.encode())
                if self.path == "/eSCL/ScannerStatus":
                    state = "ScannerAdfLoaded" if printer.feeder else "ScannerAdfEmpty"
                    return self.reply(200, f'<scan:ScannerStatus xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03"><scan:AdfState>{state}</scan:AdfState></scan:ScannerStatus>'.encode())
                if self.path.startswith("/eSCL/ScanJobs/") and self.path.endswith("/NextDocument"):
                    if printer.busy_once:
                        printer.busy_once = False
                        return self.reply(503)
                    if not printer.feeder:
                        return self.reply(404)
                    return self.reply(200, printer.feeder.pop(0), "image/jpeg")
                self.reply(404)

            def do_POST(self):
                if self.path == "/eSCL/ScanJobs":
                    printer.jobs.append(self.rfile.read(int(self.headers["Content-Length"])).decode())
                    return self.reply(201, headers=[("Location", f"/eSCL/ScanJobs/job{len(printer.jobs)}")])
                self.reply(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/eSCL"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
