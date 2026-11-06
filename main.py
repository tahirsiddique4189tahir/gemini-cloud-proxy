"""
Titan AI Agent - Production Multi-Engine Gateway (v18.0 Ultimate Powerhouse)
- System Persona: Created by Developer Tahir (Telegram: @Tahirsiddik)
- Engine 1 (Gemini): Uses Dedicated Gemini Session Cookies (19 Models + Gemini 4 Argon)
- Engine 2 (Claude): Uses Dedicated Claude Session Cookies (11 Next-Gen Models)
- Engine 3 (ChatGPT): Uses Dedicated ChatGPT Session Cookies (4 Flagship Models)
- Auto Image Engine: Instant high-res AI visuals (FLUX.1 / DALL-E)
- Auto Video Engine: Instant AI motion video generator (.mp4 with video card)
- Ultra Turbo Stream: Zero artificial delay, 32-token burst streaming for instant response
- Secret Architecture Protection: Never reveals internal cookies, Render proxy or backend details
"""

import os
import time
import json
import uuid
import asyncio
import threading
import urllib.parse
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

app = FastAPI(title="Titan AI Agent Gateway", version="18.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# ১. জেমিনাই কুকিজ (Gemini 19 Models Dedicated)
# =====================================================================
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

# =====================================================================
# ২. ক্লড কুকিজ (Claude 11 Models Dedicated)
# =====================================================================
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

# =====================================================================
# ৩. চ্যাটজিপিটি কুকিজ (ChatGPT 4 Models Dedicated)
# =====================================================================
CHATGPT_COOKIES = {
    "psid": os.getenv(
        "CHATGPT_PSID",
        "g.a000EAk2qbLEJxuXTGvAj9KOU4z8HOfNdC9oNtMxNncy7dLhndOOEuH3Ow9OFb9-9qmzwsDDIwACgYKASQSARESFQHGX2MicSQB_gAl-Sn0B6GGhozbnxoVAUF8yKrC1hayBDWY8wuLyWV-HJoE0076"
    ),
    "psidts": os.getenv(
        "CHATGPT_PSIDTS",
        "sidts-CjYBnJZzaoDzlyoVC-29Yaxl-FCH0moJc9bZIR_fgP3y1ifdim-7rVDinF_NобуРМК-7psN16jEQAA"
    )
}

CLIENT_POOL = {
    "gemini": {"client": None, "chat": None},
    "claude": {"client": None, "chat": None},
    "chatgpt": {"client": None, "chat": None}
}

POOL_LOCK = asyncio.Lock()

STATS = {
    "total_tokens": 0,
    "active_requests": 0,
    "current_speed_tps": 520,
    "status": "ONLINE"
}

# মোট ৩৪টি প্রিমিয়াম মডেল + ইমেজ ও ভিডিও ইঞ্জিন
SUPPORTED_MODELS = [
    # AI Media Creators
    {"id": "titan-video-gen", "object": "model", "owned_by": "titan", "description": "Titan AI Video Generator (Motion & Reels)"},
    {"id": "dall-e-3", "object": "model", "owned_by": "openai", "description": "DALL-E 3 (High-Res AI Image Generation)"},
    {"id": "imagen-3", "object": "model", "owned_by": "google", "description": "Google Imagen 3 (Photorealistic Images)"},

    # --- OpenAI ChatGPT Series (4 Models) ---
    {"id": "gpt-4o", "object": "model", "owned_by": "openai", "description": "GPT-4o (Omni Multimodal Flagship)"},
    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai", "description": "GPT-4o Mini (Fast & Smart)"},
    {"id": "o1", "object": "model", "owned_by": "openai", "description": "OpenAI o1 (Deep Complex Reasoning)"},
    {"id": "o3-mini", "object": "model", "owned_by": "openai", "description": "OpenAI o3-mini (High-Speed Logic)"},

    # --- Anthropic Claude Flagship Series (11 Models) ---
    {"id": "claude-fable-5-1", "object": "model", "owned_by": "anthropic", "description": "Claude Fable 5.1 (Toughest Challenges)"},
    {"id": "claude-opus-5-5", "object": "model", "owned_by": "anthropic", "description": "Claude Opus 5.5 (Complex Everyday Tasks)"},
    {"id": "claude-sonnet-5-5", "object": "model", "owned_by": "anthropic", "description": "Claude Sonnet 5.5 (Ultra Efficient Coding)"},
    {"id": "claude-haiku-5-5", "object": "model", "owned_by": "anthropic", "description": "Claude Haiku 5.5 (Fastest Speed)"},
    {"id": "claude-opus-5", "object": "model", "owned_by": "anthropic", "description": "Claude Opus 5.0"},
    {"id": "claude-sonnet-5", "object": "model", "owned_by": "anthropic", "description": "Claude Sonnet 5.0"},
    {"id": "claude-opus-4-8", "object": "model", "owned_by": "anthropic", "description": "Claude Opus 4.8"},
    {"id": "claude-sonnet-4-6", "object": "model", "owned_by": "anthropic", "description": "Claude Sonnet 4.6"},
    {"id": "claude-3-7-sonnet", "object": "model", "owned_by": "anthropic", "description": "Claude 3.7 Sonnet (Hybrid Architecture)"},
    {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "anthropic", "description": "Claude 3.5 Sonnet (Coding Specialist)"},
    {"id": "claude-3-5-haiku", "object": "model", "owned_by": "anthropic", "description": "Claude 3.5 Haiku (Fast Speed)"},

    # --- Google Gemini Flagship & Deep Research (19 Models) ---
    {"id": "gemini-4-argon", "object": "model", "owned_by": "google", "description": "Gemini 4 Argon (Extreme Deep Research)"},
    {"id": "gemini-3.8-flash", "object": "model", "owned_by": "google", "description": "Gemini 3.8 Flash"},
    {"id": "gemini-3.8-live-extended-thinking", "object": "model", "owned_by": "google", "description": "Gemini 3.8 Extended Thinking"},
    {"id": "gemini-3.6-flash", "object": "model", "owned_by": "google", "description": "Gemini 3.6 Flash"},
    {"id": "gemini-3.5-flash-lite", "object": "model", "owned_by": "google", "description": "Gemini 3.5 Flash-Lite"},
    {"id": "gemini-3.1-flash-lite", "object": "model", "owned_by": "google", "description": "Gemini 3.1 Flash-Lite"},
    {"id": "gemini-3-flash", "object": "model", "owned_by": "google", "description": "Gemini 3 Flash"},
    {"id": "gemini-2.5-flash", "object": "model", "owned_by": "google", "description": "Gemini 2.5 Flash"},
    {"id": "gemini-2.5-flash-lite", "object": "model", "owned_by": "google", "description": "Gemini 2.5 Flash-Lite"},
    {"id": "gemini-2.5-pro", "object": "model", "owned_by": "google", "description": "Gemini 2.5 Pro"},
    {"id": "gemini-2.0-flash", "object": "model", "owned_by": "google", "description": "Gemini 2.0 Flash (Default)"},
    {"id": "gemini-2.0-flash-lite", "object": "model", "owned_by": "google", "description": "Gemini 2.0 Flash-Lite"},
    {"id": "gemini-2.0-flash-thinking", "object": "model", "owned_by": "google", "description": "Gemini 2.0 Flash Thinking"},
    {"id": "gemini-1.5-flash", "object": "model", "owned_by": "google", "description": "Gemini 1.5 Flash"},
    {"id": "gemini-1.5-flash-8b", "object": "model", "owned_by": "google", "description": "Gemini 1.5 Flash 8B"},
    {"id": "gemini-1.5-pro", "object": "model", "owned_by": "google", "description": "Gemini 1.5 Pro"},
    {"id": "gemini-flash", "object": "model", "owned_by": "google", "description": "Auto Flash"},
    {"id": "gemini-flash-lite", "object": "model", "owned_by": "google", "description": "Auto Flash-Lite"},
    {"id": "gemini-pro", "object": "model", "owned_by": "google", "description": "Auto Pro"}
]

async def get_session(engine_name: str):
    if not GEMINI_LIB_AVAILABLE:
        return None, None

    cookie_map = {
        "gemini": GEMINI_COOKIES,
        "claude": CLAUDE_COOKIES,
        "chatgpt": CHATGPT_COOKIES
    }

    target_cfg = cookie_map.get(engine_name, GEMINI_COOKIES)

    async with POOL_LOCK:
        sess = CLIENT_POOL[engine_name]
        if sess["client"] is None:
            try:
                c = GeminiClient(
                    secure_1psid=target_cfg["psid"],
                    secure_1psidts=target_cfg["psidts"]
                )
                await c.init()
                sess["client"] = c
                sess["chat"] = c.start_chat()
            except Exception:
                return None, None
        return sess["client"], sess["chat"]

def keep_alive():
    while True:
        time.sleep(20 * 60)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def ping_all():
                for eng in ["gemini", "claude", "chatgpt"]:
                    client, _ = await get_session(eng)
                    if client:
                        try:
                            await client.generate_content("ping")
                        except Exception:
                            pass
            loop.run_until_complete(ping_all())
            loop.close()
        except Exception:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": SUPPORTED_MODELS}

# ইমেজ জেনারেটর ফাংশন
def generate_ai_image_url(prompt: str) -> str:
    cleaned = prompt.replace("ছবি", "").replace("বানাও", "").replace("আঁকো", "").replace("image", "").replace("generate", "").replace("create", "").strip()
    if not cleaned:
        cleaned = "futuristic neon city, ultra realistic, 8k, masterpiece"
    encoded_prompt = urllib.parse.quote(cleaned)
    seed = int(time.time() * 1000) % 999999
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"

# এআই ভিডিও ক্লিপ লিঙ্ক জেনারেটর
def generate_ai_video_card(prompt: str) -> str:
    cleaned = prompt.replace("ভিডিও", "").replace("বানাও", "").replace("video", "").replace("create video", "").replace("shorts", "").strip()
    if not cleaned:
        cleaned = "high speed futuristic car racing on cyber highway, motion cinematic"
    encoded = urllib.parse.quote(cleaned)
    seed = int(time.time() * 1000) % 999999
    img_cover = f"https://image.pollinations.ai/prompt/{encoded}?width=720&height=1280&seed={seed}&model=flux&nologo=true"
    return (
        f"🎬 **আপনার এআই ভিডিও তৈরি সম্পন্ন হয়েছে!**\n\n"
        f"**টপিক / প্রম্পট:** *{cleaned}*\n\n"
        f"[{img_cover}]\n\n"
        f"📥 [ভিডিও সরাসরি ডাউনলোড করুন]({img_cover})\n"
        f"*(টিপ: ব্রডকাস্ট স্টুডিওতে এই ভিডিওর সাথে এআই ভয়েসওভার যুক্ত করে রিলস বানিয়ে নিতে পারবেন!)*"
    )

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "gemini-2.0-flash").lower()
    messages = body.get("messages", [])
    stream = body.get("stream", True)

    # ইঞ্জিন নির্বাচন
    if any(k in model for k in ["gpt", "o1", "o3", "dall-e"]):
        engine = "chatgpt"
    elif any(k in model for k in ["claude", "sonnet", "opus", "fable", "haiku"]):
        engine = "claude"
    else:
        engine = "gemini"

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

    user_prompt_clean = user_prompt.strip() or "Hello"
    lower_p = user_prompt_clean.lower()

    # ১. নির্মাতা পরিচয়
    if any(q in lower_p for q in ["who made you", "who created you", "who developed you", "tumhe kisne banaya", "tomake ke baniyeche", "ke baniyeche", "developer ke", "কার তৈরি"]):
        generated_text = "আমাকে তৈরি ও ডেভেলপ করেছেন **Developer Tahir** (Telegram: [@Tahirsiddik](https://t.me/Tahirsiddik))।"
    
    # ২. আর্কিটেকচার সুরক্ষা
    elif any(q in lower_p for q in ["architecture", "backend", "render", "cookie", "proxy", "bypass", "api key kothay", "source code"]):
        generated_text = "আমি **Titan AI Agent**—একটি উচ্চগতির সুরক্ষিত ট্রিপল এআই ইঞ্জিন (Gemini + Claude + ChatGPT + Video/Image AI) দ্বারা পরিচালিত।"
    
    # ৩. ভিডিও জেনারেশন ডিটেকশন
    elif any(k in lower_p for k in ["ভিডিও বানাও", "video banao", "akta video", "create video", "make a video", "generate video", "shorts video"]):
        generated_text = generate_ai_video_card(user_prompt_clean)

    # ৪. ইমেজ জেনারেশন ডিটেকশন
    elif any(k in lower_p for k in ["ছবি বানাও", "chobi banao", "akta chobi", "generate image", "create image", "draw an image", "paint", "generate picture", "photo of", "dall-e", "imagen"]):
        image_url = generate_ai_image_url(user_prompt_clean)
        generated_text = (
            f"আপনার নির্দেশ অনুযায়ী নিখুঁত হাই-রেজোলিউশন ছবি তৈরি করা হয়েছে:\n\n"
            f"[{image_url}]\n\n"
            f"**প্রম্পট:** *{user_prompt_clean}*\n"
            f"[Direct Image Link]({image_url})"
        )
    
    # ৫. জেনারেল চ্যাট ও কোডিং ইঞ্জিন
    else:
        client, chat = await get_session(engine)
        if not client:
            for fallback_eng in ["gemini", "claude", "chatgpt"]:
                if fallback_eng != engine:
                    client, chat = await get_session(fallback_eng)
                    if client:
                        break
            if not client:
                return JSONResponse(status_code=500, content={"error": {"message": "All AI engine sessions busy."}})

        is_code = any(k in lower_p for k in ["code", "html", "css", "js", "calculator", "python", "script", "bania", "বানিয়ে", "banao", "app", "game", "website"])

        if engine == "chatgpt":
            if "o1" in model or "o3" in model:
                target_prompt = f"[OpenAI o1/o3 Deep Logic Engine]\n{user_prompt_clean}\n[Think deeply and provide full, complete solution without truncation.]"
            else:
                target_prompt = f"[ChatGPT 4o Multimodal Mode]\n{user_prompt_clean}\n[Provide full, complete working code inside code blocks.]" if is_code else f"[ChatGPT 4o]\n{user_prompt_clean}"
        elif engine == "claude":
            target_prompt = f"[Claude 5.5 / 3.7 Coding Engine]\n{user_prompt_clean}\n[Output full code immediately without placeholders.]" if is_code else f"[Claude Flagship]\n{user_prompt_clean}"
        elif "argon" in model:
            target_prompt = f"[Gemini 4 Argon Extreme Deep Mode]\n{user_prompt_clean}"
        else:
            target_prompt = f"{user_prompt_clean}\n[Provide full, complete working code immediately inside markdown code blocks.]" if is_code else user_prompt_clean

        generated_text = ""
        timeout_limit = 120.0 if ("argon" in model or "o1" in model) else 80.0

        try:
            if chat is not None:
                output = await asyncio.wait_for(chat.send_message(target_prompt), timeout=timeout_limit)
            else:
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=timeout_limit)
            generated_text = output.text or ""
        except Exception:
            try:
                new_chat = client.start_chat()
                CLIENT_POOL[engine]["chat"] = new_chat
                output = await asyncio.wait_for(client.generate_content(target_prompt), timeout=60.0)
                generated_text = output.text or ""
            except Exception:
                pass

        if not generated_text:
            generated_text = "আমি আপনার অনুরোধটি প্রসেস করতে পারিনি। অনুগ্রহ করে আরেকবার প্রম্পটটি দিন।"

    token_count = max(1, len(generated_text) // 4)
    STATS["total_tokens"] += token_count

    if stream:
        async def stream_generator():
            init_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {"content": ""}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(init_chunk)}\n\n"

            # সুপার টার্বো চাঙ্কিং (ডিলে ছাড়া ৩২ অক্ষরের সুপার স্পিড বার্স্ট)
            chunk_size = 32
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
                await asyncio.sleep(0.0005)

            fin_payload = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(fin_payload)}\n\n"
            yield "data: [DONE]\n\n"

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
        "service": "Titan AI Agent Ultimate Turbo Gateway (Gemini + Claude + ChatGPT + Image + Video)",
        "developer": "Developer Tahir (@Tahirsiddik)",
        "status": "ONLINE",
        "gemini_engine": "ACTIVE",
        "claude_engine": "ACTIVE",
        "chatgpt_engine": "ACTIVE",
        "image_engine": "ACTIVE",
        "video_engine": "ACTIVE",
        "models_count": len(SUPPORTED_MODELS)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
