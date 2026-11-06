"""
Titan AI Agent - Production Gateway (v9.8.0 High-Speed Engine)
- System Persona: Created by Developer Tahir (Telegram: @Tahirsiddik)
- Strict Rule: Direct answers without repetitive generic salam greetings
- Secret Architecture Protection: Never reveals internal cookies, Render proxy or backend details
- Long Code & Complex Script Optimization: Zero bot trigger & instant SSE keep-alive stream
"""

import os
import time
import json
import uuid
import asyncio
import threading
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    from gemini_webapi import GeminiClient
    GEMINI_LIB_AVAILABLE = True
except ImportError:
    GEMINI_LIB_AVAILABLE = False

app = FastAPI(title="Titan AI Agent Gateway", version="9.8.0")

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
    "current_speed_tps": 320,
    "status": "INITIALIZING"
}

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
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "titan", "description": "Gemini 2.0 Flash (Default)"},
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
                    await client.generate_content("hello")
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
    stream = body.get("stream", True)

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

    if any(q in lower_p for q in ["who made you", "who created you", "who developed you", "tumhe kisne banaya", "tomake ke baniyeche", "ke baniyeche", "developer ke", "কার তৈরি", "maker ke"]):
        generated_text = "আমাকে তৈরি ও ডেভেলপ করেছেন **Developer Tahir** (Telegram: [@Tahirsiddik](https://t.me/Tahirsiddik))।"
    
    elif any(q in lower_p for q in ["architecture", "backend", "render", "cookie", "proxy", "bypass", "api key kothay", "source code"]):
        generated_text = "আমি **Titan AI Agent**—একটি উচ্চগতির সুরক্ষিত অটোনোমাস এআই ইঞ্জিন দ্বারা পরিচালিত। আমার অভ্যন্তরীণ ব্যাকএন্ড এবং আর্কিটেকচার সম্পূর্ণ এনক্রিপ্টেড ও সুরক্ষিত।"
    
    else:
        client, chat = await get_or_init_client()
        if not client:
            return JSONResponse(status_code=500, content={"error": {"message": "Gateway client not ready."}})

        target_prompt = user_prompt_clean

        generated_text = ""
        try:
            if chat is not None:
                output = await asyncio.wait_for(chat.send_message(target_prompt), timeout=85.0)
            else:
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=85.0)
            generated_text = output.text or ""
        except Exception:
            try:
                CURRENT_CHAT = client.start_chat()
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=60.0)
                generated_text = output.text or ""
            except Exception:
                pass

        if not generated_text:
            generated_text = "আমি আপনার অনুরোধটি প্রসেস করতে পারিনি। অনুগ্রহ করে আরেকবার প্রম্পটটি দিন।"

    token_count = max(1, len(generated_text) // 4)
    STATS["total_tokens"] += token_count
    STATS["current_speed_tps"] = 320

    if stream:
        async def stream_generator():
            try:
                init_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": ""}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(init_chunk)}\n\n"

                chunk_size = 12
                for i in range(0, len(generated_text), chunk_size):
                    chunk_str = generated_text[i:i+chunk_size]
                    payload = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": chunk_str}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.005)

                fin_payload = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(fin_payload)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                pass

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": generated_text}, "finish_reason": "stop"}],
            "usage": {"total_tokens": token_count}
        }

@app.get("/")
async def root():
    return {
        "service": "Titan AI Agent Gateway",
        "developer": "Developer Tahir (@Tahirsiddik)",
        "status": STATS["status"],
        "models_count": len(SUPPORTED_MODELS)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
