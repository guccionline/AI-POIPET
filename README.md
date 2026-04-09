# C AI — Chat UI (Local Hosting)

Aplikasi chat sederhana berbasis **FastAPI** (backend) + **HTML/CSS/JS** (frontend) dengan fitur:

- Chat streaming (SSE)
- Tampilan Markdown rapi (heading, list, tabel)
- Kirim **gambar** (attach / paste `Ctrl+V`) + preview
- Kirim **kode** (code block) dengan tombol **Copy**

## Prasyarat

- Windows 10/11
- Python 3.11+ (disarankan 3.13/3.14)
- API key Groq (environment variable `GROQ_API_KEY`)

## Install (sekali saja)

Di PowerShell:

```powershell
cd "C:\Users\kurakuraninja\Desktop\chat-ui"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn groq python-multipart
```

Catatan:
- `python-multipart` diperlukan untuk upload gambar.

## Set API Key (wajib)

### Opsi A — untuk sesi terminal saat ini (paling cepat)

```powershell
$env:GROQ_API_KEY="ISI_API_KEY_KAMU"
```

### Opsi B — permanen untuk user Windows

```powershell
[Environment]::SetEnvironmentVariable("GROQ_API_KEY","ISI_API_KEY_KAMU","User")
```

Lalu **tutup & buka lagi** PowerShell/Cursor/VSCode agar env terbaca.

## Menjalankan Server

Aktifkan venv lalu jalankan uvicorn:

```powershell
cd "C:\Users\kurakuraninja\Desktop\chat-ui"
.\.venv\Scripts\Activate.ps1
python -m uvicorn server:app --host 0.0.0.0 --port 8081
```

Buka di browser:

- `http://127.0.0.1:8081`

## Cara Pakai

- **Kirim teks**: ketik lalu tekan `Enter` (atau klik tombol `↑`)
- **Baris baru**: `Shift + Enter`
- **Kirim gambar**:
  - Klik tombol `＋` lalu pilih gambar, atau
  - Paste screenshot/gambar langsung dengan `Ctrl + V`
- **Kirim kode**: bungkus dengan triple backtick:

```text
```python
print("halo")
```
```

## Troubleshooting

### 1) Muncul `[Error] GROQ_API_KEY belum diset...`

Berarti proses server tidak melihat env var.

Di PowerShell yang sama:

```powershell
echo $env:GROQ_API_KEY
python -c "import os; print('has_key=', bool(os.environ.get('GROQ_API_KEY')))"
```

Jika `has_key=False`, set lagi:

```powershell
$env:GROQ_API_KEY="ISI_API_KEY_KAMU"
```

Lalu restart uvicorn.

### 2) Port sudah dipakai (WinError 10048)

Pakai port lain, misalnya 8082:

```powershell
python -m uvicorn server:app --host 0.0.0.0 --port 8082
```

Atau cari PID yang pakai port 8081:

```powershell
netstat -ano | findstr :8081
taskkill /PID PID_KAMU /F
```

### 3) AI “diam” / stuck

Biasanya karena env key tidak kebaca atau request gagal.
Lihat bubble AI: jika ada `[Error] ...`, copy error tersebut.

## Struktur Folder

- `server.py` — FastAPI server (endpoint chat streaming + upload gambar)
- `static/index.html` — UI frontend
- `uploads/` — hasil upload gambar (dibuat otomatis)

