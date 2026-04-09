import os
import uuid
from pathlib import Path
import json

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

_GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=_GROQ_API_KEY) if _GROQ_API_KEY else None


@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")


@app.get("/")
def index():
    return FileResponse("static/index.html")


SYSTEM_PROMPT = """
Kamu adalah asisten profesional. Tulis jawaban yang rapi dan mudah dibaca di chat UI.

ATURAN WAJIB:
- Jika user bertanya "siapa kamu", "kamu siapa", "perkenalan", atau pertanyaan identitas sejenis, jawaban WAJIB persis seperti berikut (gunakan Markdown, pertahankan baris baru):

Perkenalan

Saya adalah C AI POIPET, asisten virtual berbasis AI yang dikembangkan oleh Master POIPET.  
Tujuan saya adalah membantu menjawab pertanyaan, memberikan saran, atau membuat konten sesuai kebutuhan Anda.  
Saya dapat berkomunikasi dalam bahasa Indonesia dan banyak bahasa lainnya, serta menyajikan informasi dalam format yang rapi dan mudah dibaca.  
Jika ada hal spesifik yang ingin Anda ketahui atau butuh bantuan, silakan beri tahu saya!

- Selalu pakai baris baru (newline) untuk struktur. Jangan gabungkan banyak poin dalam satu baris.
- Gunakan Markdown yang bersih: judul (##), subjudul (###), bullet list (-), dan tabel Markdown (dengan |).
- Untuk bullet list, setiap poin HARUS diawali "- " di awal baris (bukan " - poin - poin" dalam satu kalimat).
- Untuk jadwal/piket mingguan, gunakan format seperti ini:
  1) Judul: "## Jadwal Piket Poskamling (Mingguan)"
  2) Tabel Markdown STANDAR dengan header yang jelas.
     - Setiap baris tabel WAJIB diawali dan diakhiri karakter "|"
     - Baris ke-2 WAJIB separator markdown (contoh: "| --- | --- | --- | --- |")
     - Jangan gunakan tabel ASCII/art (garis panjang, "====", "----" tanpa format markdown)
     - WAJIB ada 1 baris kosong sebelum tabel, dan setiap row tabel di baris baru (jangan 1 baris panjang).
  3) Setelah tabel, tambahkan bagian "### Catatan:" berupa bullet list bila ada aturan tambahan.
- Jangan tampilkan JSON mentah kecuali user memintanya.
"""


@app.post("/api/chat")
async def chat(request: Request):
    if client is None:
        def sse_err():
            yield "data: [Error] GROQ_API_KEY belum diset. Set environment variable GROQ_API_KEY lalu restart server.\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            sse_err(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    body = await request.json()
    messages = body.get("messages", [])

    # Normalisasi content agar kompatibel (beberapa model tidak menerima multimodal array).
    norm = []
    for m in messages:
        role = (m or {}).get("role", "user")
        content = (m or {}).get("content", "")
        if isinstance(content, list):
            parts = []
            for p in content:
                if not isinstance(p, dict):
                    continue
                if p.get("type") == "text" and isinstance(p.get("text"), str):
                    parts.append(p["text"])
                elif p.get("type") == "image_url":
                    iu = p.get("image_url") or {}
                    url = iu.get("url")
                    if url:
                        parts.append(f"[image] {url}")
            content = "\n".join([x for x in parts if x]).strip()
        elif content is None:
            content = ""
        else:
            content = str(content)
        norm.append({"role": role, "content": content})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + norm

    model = body.get("model", "openai/gpt-oss-120b")
    temperature = body.get("temperature", 0.5)
    top_p = body.get("top_p", 1)
    max_tokens = body.get("max_completion_tokens", 2048)
    reasoning_effort = body.get("reasoning_effort", "medium")

    def sse_stream():
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_completion_tokens=max_tokens,
                reasoning_effort=reasoning_effort,
                stream=True,
            )

            for chunk in completion:
                # Groq stream: delta bisa kosong
                delta = ""
                try:
                    delta = chunk.choices[0].delta.content or ""
                except Exception:
                    delta = ""
                if not delta:
                    continue
                # SSE aman untuk newline: kirim sebagai JSON string (escaped)
                yield "data: " + json.dumps(delta, ensure_ascii=False) + "\n\n"
        except Exception as e:
            msg = f"[Error] {type(e).__name__}: {e}"
            yield "data: " + json.dumps(msg, ensure_ascii=False) + "\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        return {"error": "Only image uploads are supported."}

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        ct = (file.content_type or "").lower()
        ext = (
            ".png"
            if "png" in ct
            else ".jpg"
            if "jpeg" in ct or "jpg" in ct
            else ".webp"
            if "webp" in ct
            else ".gif"
            if "gif" in ct
            else ".bin"
        )

    name = f"{uuid.uuid4().hex}{ext}"
    out_path = UPLOAD_DIR / name
    data = await file.read()
    out_path.write_bytes(data)
    return {"url": f"/uploads/{name}", "content_type": file.content_type, "size": len(data)}