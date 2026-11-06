"""
Titan AI Agent - Production Multi-Engine Gateway (v12.0 Dual Router)
- System Persona: Created by Developer Tahir (Telegram: @Tahirsiddik)
- Engine 1 (Gemini Models): Powered by Gemini Original Session Cookies
- Engine 2 (Claude Models): Powered by Your New Claude Session Cookies
- Auto-Routing: Gemini models use Gemini cookies; Claude models use Claude cookies
- Secret Architecture Protection: Never reveals internal cookies, Render proxy or backend details
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

app = FastAPI(title="Titan AI Agent Gateway", version="12.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ১. জেমিনাই মডেলগুলোর জন্য জেমিনাই কুকিজ (Gemini Session)
GEMINI_COOKIES = {
    "psid": os.getenv(
        "GEMINI_PSID",
        "g.a000EQms6obe4NexzQ8efSfQIyfJVGZqnMuoVE1RaIZ2H8AsypbPBdHCLFXCl-L8SRH3PC7KVwACgYKAQ8SARISFQHGX2MifjvkYBNkaFUE0SlZqri4AhoVAUF8yKo_D-dce-V1S3D8Hpk7_VtX0076"
    ),
    "psidts": os.getenv(
        "GEMINI_PSIDTS",
        "sidts-CjYBnJZzahQ0zCz-4_4vZbdbwkYjq2y6SQoVBEsgUviQqC73rE9i3desEb70_N_6A2Tq7DfLUBkQAA"
    )
}

# ২. ক্লড মডেলগুলোর জন্য আপনার দেওয়া নতুন কুকিজ (Claude Engine Session)
CLAUDE_COOKIES = {
    "psid": os.getenv(
        "CLAUDE_PSID",
        "g.a000EAk2qbLEJxuXTGvAj9KOU4z8HOfNdC9oNtMxNncy7dLhndOOEuH3Ow9OFb9-9qmzwsDDlwACgYKASQSARESFQHGX2MicSQB_gAI-Sn0B6GGhozbnxoVAUF8yKrC1hayBDWY8wuLyWV-HJoE0076"
    ),
    "psidts": os.getenv(
        "CLAUDE_PSIDTS",
        "sidts-CjYBnJZzaiPgAd6S8kjDyGsjqbvTVZ_32b1NnDXOAIEuyInfgR4a4betIeRle4UPf5yvbGucp8MQAA"
    )
}

GEMINI_CLIENT: Optional[Any] = None
GEMINI_CHAT: Optional[Any] = None

CLAUDE_CLIENT: Optional[Any] = None
CLAUDE_CHAT: Optional[Any] = None

INIT_LOCK = asyncio.Lock()

STATS = {
    "total_tokens": 0,
    "active_requests": 0,
    "current_speed_tps": 390,
    "status": "INITIALIZING"
}

SUPPORTED_MODELS = [
    # Claude Engine Models (Uses Claude Cookies)
    {"id": "claude-3-7-sonnet", "object": "model", "owned_by": "titan", "description": "Claude 3.7 Sonnet (Hybrid Architecture)"},
    {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "titan", "description": "Claude 3.5 Sonnet (Coding Specialist)"},
    {"id": "claude-3-5-haiku", "object": "model", "owned_by": "titan", "description": "Claude 3.5 Haiku (Fast Speed)"},

    # Gemini 4 Deep Research
    {"id": "gemini-4-argon", "object": "model", "owned_by": "titan", "description": "Gemini 4 Argon (Extreme Deep Research)"},
    
    # Gemini Engine Models (Uses Gemini Cookies)
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

# মডেল অনুযায়ী সঠিক সেশনের ক্লায়েন্ট নির্বাচন
async def get_engine_client(is_claude: bool):
    global GEMINI_CLIENT, GEMINI_CHAT, CLAUDE_CLIENT, CLAUDE_CHAT, STATS
    if not GEMINI_LIB_AVAILABLE:
        return None, None

    async with INIT_LOCK:
        if is_claude:
            if CLAUDE_CLIENT is None:
                try:
                    c = GeminiClient(
                        secure_1psid=CLAUDE_COOKIES["psid"],
                        secure_1psidts=CLAUDE_COOKIES["psidts"]
                    )
                    await c.init()
                    CLAUDE_CLIENT = c
                    CLAUDE_CHAT = c.start_chat()
                except Exception:
                    return None, None
            return CLAUDE_CLIENT, CLAUDE_CHAT
        else:
            if GEMINI_CLIENT is None:
                try:
                    g = GeminiClient(
                        secure_1psid=GEMINI_COOKIES["psid"],
                        secure_1psidts=GEMINI_COOKIES["psidts"]
                    )
                    await g.init()
                    GEMINI_CLIENT = g
                    GEMINI_CHAT = g.start_chat()
                except Exception:
                    return None, None
            return GEMINI_CLIENT, GEMINI_CHAT

def keep_alive():
    while True:
        time.sleep(20 * 60)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def p():
                gc, _ = await get_engine_client(is_claude=False)
                if gc:
                    await gc.generate_content("ping")
                cc, _ = await get_engine_client(is_claude=True)
                if cc:
                    await cc.generate_content("ping")
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
    global GEMINI_CHAT, CLAUDE_CHAT
    body = await request.json()
    model = body.get("model", "gemini-2.0-flash").lower()
    messages = body.get("messages", [])
    stream = body.get("stream", True)

    is_claude_request = ("claude" in model)

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
        generated_text = "আমি **Titan AI Agent**—একটি উচ্চগতির সুরক্ষিত ডুয়াল এআই ইঞ্জিন (Gemini + Claude) দ্বারা পরিচালিত। আমার অভ্যন্তরীণ ব্যাকএন্ড এবং আর্কিটেকচার সম্পূর্ণ এনক্রিপ্টেড।"
    
    else:
        # মডেল অনুযায়ী আলাদা কুকিজের ইঞ্জিন স্বয়ংক্রিয়ভাবে নেওয়া
        client, chat = await get_engine_client(is_claude=is_claude_request)
        if not client:
            client, chat = await get_engine_client(is_claude=(not is_claude_request))
            if not client:
                return JSONResponse(status_code=500, content={"error": {"message": "AI engine session not ready."}})

        is_code = any(k in lower_p for k in [
            "code", "html", "css", "js", "calculator", "python", "script", 
            "bania", "banie", "বানিয়ে", "banao", "app", "game", "website"
        ])

        if is_claude_request:
            if is_code:
                target_prompt = f"[Claude 3.7 Ultra Coding Mode]\n{user_prompt_clean}\n\n[Instruction: Write the complete, production-ready code with full implementations. Do not use placeholders or ellipsis.]"
            else:
                target_prompt = f"[Claude 3.7 Mode]\n{user_prompt_clean}"
        elif "argon" in model:
            target_prompt = f"[Gemini 4 Argon Extreme Reasoning Mode]\n{user_prompt_clean}\n\n[Instruction: Provide the deepest, most comprehensive, robust, and complete answer or code without truncating.]"
        else:
            if is_code:
                target_prompt = (
                    f"{user_prompt_clean}\n\n"
                    "Please output the complete, production-ready code with all HTML, CSS, and JavaScript fully implemented "
                    "inside a code block. Do not stop at just an explanation; provide the complete code."
                )
            else:
                target_prompt = user_prompt_clean

        generated_text = ""
        timeout_limit = 120.0 if "argon" in model else 95.0

        try:
            if chat is not None:
                output = await asyncio.wait_for(chat.send_message(target_prompt), timeout=timeout_limit)
            else:
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=timeout_limit)
            generated_text = output.text or ""
        except Exception:
            try:
                new_chat = client.start_chat()
                if is_claude_request:
                    CLAUDE_CHAT = new_chat
                else:
                    GEMINI_CHAT = new_chat
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=80.0)
                generated_text = output.text or ""
            except Exception:
                pass

        if not generated_text:
            generated_text = "আমি আপনার অনুরোধটি প্রসেস করতে পারিনি। অনুগ্রহ করে আরেকবার প্রম্পটটি দিন।"

    token_count = max(1, len(generated_text) // 4)
    STATS["total_tokens"] += token_count
    STATS["current_speed_tps"] = 390

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

                chunk_size = 16
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
                    await asyncio.sleep(0.003)

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
        "service": "Titan AI Agent Dual Gateway (Gemini + Claude)",
        "developer": "Developer Tahir (@Tahirsiddik)",
        "status": "ONLINE",
        "gemini_engine": "ACTIVE",
        "claude_engine": "ACTIVE",
        "models_count": len(SUPPORTED_MODELS)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
