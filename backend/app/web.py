"""Helpers shared by the API routers."""
from fastapi import HTTPException, Request

from . import db
from .parse import file_text


def get_or_404(c, table, id_):
    r = db.row(c.execute(f"SELECT * FROM {table} WHERE id=?", (id_,)).fetchone())
    if r is None:
        raise HTTPException(404, f"{table} {id_} not found")
    return r


async def text_or_file(req: Request) -> str:
    """Body is either JSON {"text": ...} (paste) or multipart with `file` (upload)."""
    if req.headers.get("content-type", "").startswith("multipart/"):
        form = await req.form()
        f = form.get("file")
        if f is None:
            raise HTTPException(422, "missing file")
        return file_text(f.filename or "", await f.read())
    if not req.headers.get("content-type", "").startswith("application/json"):
        raise HTTPException(415, "send JSON (application/json) or a file upload")
    try:
        body = await req.json()
    except ValueError:
        raise HTTPException(422, "body is not valid JSON") from None
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise HTTPException(422, 'expected {"text": "..."}')
    return body["text"]



def png(img):
    import cv2
    from fastapi.responses import Response
    return Response(cv2.imencode(".png", img)[1].tobytes(), media_type="image/png")
