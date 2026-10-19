# Routeway AI Suite (`routeway-suite`)

Comprehensive CLI toolkit & Python SDK for **Routeway AI** (`https://routeway.ai`), the unified AI gateway providing access to **280+ AI models** (OpenAI, Anthropic, Google, DeepSeek, Mistral, Moonshot Kimi, Meta, Flux, etc.).

---

## ⚡ Fitur Utama

- **OpenAI & Anthropic Compatible**: Mendukung endpoint `/v1/chat/completions` dan `/v1/messages`.
- **280+ Model Catalog Explorer**: Query dan filter model berdasarkan provider, status `:free`, kemampuan reasoning, atau kata kunci pencarian.
- **Server Tools Built-in**: Mendukung integrasi pencarian web langsung (`@online`) dan pembuatan gambar langsung dalam percakapan (`@flux-2-turbo`).
- **Image Generation**: Endpoint `/v1/images/generations` untuk model FLUX, Ideogram V3, HiDream, Animagine XL, dll.
- **Account & Key Management**: Monitor saldo kredit USD (`/v1/account/balance`) serta otomatisasi rotasi dan pembuatan API key (`/v1/account/keys`).
- **OAuth Generator**: Pembuat link 1-click GitHub, Google, & Discord OAuth tanpa hambatan captcha.

---

## 🚀 Setup & Instalasi

CLI `routeway` sudah terpasang secara global di `/usr/local/bin/routeway`:

```bash
# Simpan API key yang didapatkan dari dashboard (format: sk-...)
routeway save-key sk-...

# Atau gunakan environment variable
export ROUTEWAY_API_KEY="sk-..."
```

---

## 📖 Panduan Penggunaan CLI

### 1. Eksplorasi Model (Termasuk Model Gratis)
```bash
# Tampilkan semua model gratis (:free)
routeway models --free

# Filter model dari Anthropic
routeway models --provider anthropic

# Cari model DeepSeek
routeway models --search deepseek
```

### 2. Chat Completion / Inferensi Model
```bash
# Chat streaming standar
routeway chat --model "claude-sonnet-5.5" --prompt "Jelaskan arsitektur Transformer secara ringkas."

# Chat dengan web search langsung (@online)
routeway chat --model "gpt-4o-mini" --web --prompt "Berita AI terbaru hari ini"

# Non-streaming
routeway chat --model "deepseek-v4-flash:free" --prompt "Halo" --no-stream
```

### 3. Generate Gambar (Image Generation)
```bash
routeway image --model "juggernaut-lightning-flux" --prompt "Cyberpunk city with neon lights, 8k resolution, highly detailed" --size "1024x1024"
```

### 4. Cek Saldo & Manajemen API Key
```bash
# Cek saldo akun
routeway balance

# List API keys yang aktif
routeway keys list

# Buat API key baru dengan limit harian
routeway keys create --label "my-bot" --limit 500

# Hapus API key berdasarkan ID
routeway keys delete --id 123
```

### 5. Generate 1-Click OAuth Sign-In Link
```bash
# Dapatkan link login instan via GitHub
routeway oauth-link --provider github

# Atau via Google / Discord
routeway oauth-link --provider google
```

---

## 🐍 Penggunaan sebagai Python SDK

```python
from routeway_suite import RoutewayClient

client = RoutewayClient(api_key="sk-...")

# 1. Chat Completion
response = client.chat_completion(
    model="claude-sonnet-5.5",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=False
)
print(response["choices"][0]["message"]["content"])

# 2. Cek Saldo
balance = client.get_balance()
print(f"Saldo: ${balance['balance']}")
```
