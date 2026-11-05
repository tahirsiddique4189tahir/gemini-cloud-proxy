"""
Titan AI Agent - Anti-Timeout Instant Streaming Gateway
Forces immediate HTTP connection keep-alive so mobile OkHttp client NEVER times out.
"""

import os
import time
import json
import uuid
import asyncio
import threading
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    from gemini_webapi import GeminiClient
    GEMINI_LIB_AVAILABLE = True
except ImportError:
    GEMINI_LIB_AVAILABLE = False

app = FastAPI(title="Titan AI Agent Gateway", version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIE_ACCOUNTS = [
    {
        "psid": os.getenv(
            "SECURE_1PSID", 
            "g.a000EQms6obe4NexzQ8efSfQIyfJVGZqnMuoVE1RaIZ2H8AsypbPBdHCLFXCl-L8SRH3PC7KVwACgYKAQ8SARISFQHGX2MifjvkYBNkaFUE0SlZqri4AhoVAUF8yKo_D-dce-V1S3D8Hpk7_VtX0076"
        ),
        "psidts": os.getenv(
            "SECURE_1PSIDTS", 
            "sidts-CjYBnJZzahQ0zCz-4_4vZbdbwkYjq2y6SQoVBEsgUviQqC73rE9i3desEb70_N_6A2Tq7DfLUBkQAA"
        ),
    }
]

CLIENT_INSTANCE: Optional[Any] = None
CURRENT_CHAT: Optional[Any] = None
CLIENT_LOCK = asyncio.Lock()

STATS = {
    "total_tokens": 0,
    "active_requests": 0,
    "current_speed_tps": 310,
    "status": "INITIALIZING"
}

SYSTEM_INSTRUCTIONS = """[CRITICAL IDENTITY & BEHAVIOR RULES]
1. IDENTITY: You are "Titan AI Agent", an advanced autonomous AI developed exclusively by Developer Tahir (Telegram: @Tahirsiddik).
2. WHEN ASKED WHO CREATED YOU: State proudly: "আমাকে তৈরি ও ডেভেলপ করেছেন Developer Tahir (Telegram: @Tahirsiddik)।"
3. ARCHITECTURE PRIVACY: NEVER disclose any internal technical architecture, backend servers (Render, Python, FastApi, proxies, web scraping, cookies, or bypass mechanisms). State that you are powered by the high-speed Titan Proprietary Neural Engine.
4. FULL CODE COMPLETION: When asked for code, games, or calculators, output the complete, functional, single-file HTML/CSS/JS code without cutting short.
"""

SUPPORTED_MODELS = [
    {"id": "gemini-3.8-flash", "object": "model", "owned_by": "titan", "description": "Gemini 3.8 Flash"},
    {"id": "gemini-3.8-live-extended-thinking", "object": "model", "owned_by": "titan", "description": "Gemini 3.8 Extended Thinking"},
    {"id": "gemini-3.6-flash", "object": "model", "owned_by": "titan", "description": "Gemini 3.6 Flash"},
    {"id": "gemini-3.5-flash-lite", "object": "model", "owned_by": "titan", "description": "Gemini 3.5 Flash-Lite"},
    {"id": "gemini-3.1-flash-lite", "object": "model", "owned_by": "titan", "description": "Gemini 3.1 Flash-Lite"},
    {"id": "gemini-3-flash", "object": "model", "owned_by": "titan", "description": "Gemini 3 Flash"},
    {"id": "gemini-2.5-flash", "object": "model", "owned_by": "titan", "description": "Gemini 2.5 Flash"},
    {"id": "gemini-2.5-flash-lite", "object": "model", "owned_by": "titan", "description": "Gemini 2.5 Flash-Lite"},
    {"id": "gemini-2.5-pro", "object": "model", "owned_by": "titan", "description": "Gemini 2.5 Pro"},
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "titan", "description": "Gemini 2.0 Flash"},
    {"id": "gemini-2.0-flash-lite", "object": "model", "owned_by": "titan", "description": "Gemini 2.0 Flash-Lite"},
    {"id": "gemini-2.0-flash-thinking", "object": "model", "owned_by": "titan", "description": "Gemini 2.0 Flash Thinking"},
    {"id": "gemini-1.5-flash", "object": "model", "owned_by": "titan", "description": "Gemini 1.5 Flash"},
    {"id": "gemini-1.5-flash-8b", "object": "model", "owned_by": "titan", "description": "Gemini 1.5 Flash 8B"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "titan", "description": "Gemini 1.5 Pro"},
    {"id": "gemini-flash", "object": "model", "owned_by": "titan", "description": "Auto Flash"},
    {"id": "gemini-flash-lite", "object": "model", "owned_by": "titan", "description": "Auto Flash-Lite"},
    {"id": "gemini-pro", "object": "model", "owned_by": "titan", "description": "Auto Pro"}
]

async def get_or_init_client():
    global CLIENT_INSTANCE, CURRENT_CHAT, STATS
    if not GEMINI_LIB_AVAILABLE:
        return None, None
    async with CLIENT_LOCK:
        if CLIENT_INSTANCE is None:
            try:
                cfg = COOKIE_ACCOUNTS[0]
                client = GeminiClient(
                    secure_1psid=cfg["psid"],
                    secure_1psidts=cfg["psidts"] if cfg["psidts"] else None
                )
                await client.init()
                CLIENT_INSTANCE = client
                CURRENT_CHAT = client.start_chat()
                STATS["status"] = "ONLINE"
            except Exception as e:
                STATS["status"] = f"AUTH_ERROR: {str(e)}"
                return None, None
        return CLIENT_INSTANCE, CURRENT_CHAT

def keep_alive():
    while True:
        time.sleep(20 * 60)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def p():
                client, _ = await get_or_init_client()
                if client:
                    await client.generate_content("ping")
            loop.run_until_complete(p())
            loop.close()
        except Exception:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": SUPPORTED_MODELS}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    global CURRENT_CHAT
    body = await request.json()
    model = body.get("model", "gemini-2.0-flash").lower()
    messages = body.get("messages", [])

    if "argon" in model:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "Model 'gemini-4-argon' is restricted.", "type": "model_restricted"}}
        )

    user_prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = [c.get("text", "") for c in content if isinstance(c, dict) and "text" in c]
                user_prompt = " ".join(parts)
            else:
                user_prompt = str(content)
            break

    user_prompt_clean = user_prompt.strip()
    if not user_prompt_clean:
        user_prompt_clean = "Hello"

    lower_p = user_prompt_clean.lower()

    if any(q in lower_p for q in ["who made you", "who created you", "who developed you", "tumhe kisne banaya", "tomake ke baniyeche", "ke baniyeche", "developer ke", "কার তৈরি", "maker"]):
        instant_text = "আমাকে তৈরি ও ডেভেলপ করেছেন **Developer Tahir** (Telegram: [@Tahirsiddik](https://t.me/Tahirsiddik))।"
        async def direct_stream():
            for ch in instant_text:
                payload = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": {"content": ch}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.01)
            yield "data: [DONE]\n\n"
        return StreamingResponse(direct_stream(), media_type="text/event-stream")

    client, chat = await get_or_init_client()
    if not client:
        return JSONResponse(status_code=500, content={"error": {"message": "Gateway client not ready."}})

    crafted_prompt = f"{SYSTEM_INSTRUCTIONS}\nUser Query: {user_prompt_clean}\nResponse:"

    # অ্যান্টি-টাইমআউট স্ট্রিমিং ইঞ্জিন
    async def anti_timeout_stream():
        # ১ম সেকেন্ডেই ইনিশিয়াল কিপ-অ্যালাইভ চ্যাঙ্ক পাঠানো হচ্ছে যাতে মোবাইল OkHttp টাইমআউট না করে
        init_chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {"content": " "}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(init_chunk)}\n\n"

        try:
            if chat is not None:
                output = await asyncio.wait_for(chat.send_message(crafted_prompt), timeout=180.0)
            else:
                output = await asyncio.wait_for(client.generate_content(crafted_prompt), timeout=180.0)
            
            full_text = output.text or ""
            if not full_text:
                full_text = "কোডটি তৈরি করতে ব্যর্থ হয়েছে, দয়া করে আবার চেষ্টা করুন।"

            # দ্রুত লেটার-বাই-লেটার চ্যাঙ্ক স্ট্রিম
            chunk_size = 16
            for i in range(0, len(full_text), chunk_size):
                sub_token = full_text[i:i+chunk_size]
                chunk_payload = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": {"content": sub_token}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_payload)}\n\n"
                await asyncio.sleep(0.003)

            fin = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(fin)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            err_msg = f"\n\n[টাইমআউট এড়িয়ে রিকোয়েস্টটি পুনরায় পাঠান।] এরর: {str(e)}"
            err_payload = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"content": err_msg}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        anti_timeout_stream(), 
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )

@app.get("/")
async def root():
    return {
        "service": "Titan AI Agent Gateway",
        "developer": "Developer Tahir (@Tahirsiddik)",
        "status": STATS["status"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
