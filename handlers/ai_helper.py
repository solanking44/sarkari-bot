import httpx
from config import GROQ_API_KEY

async def get_ai_response(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "⚠️ Groq AI Service abhi configured nahi hai."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional Sarkari Exam Expert Tutor. Answer user questions accurately, concisely, and clearly in clear Hindi/Hinglish."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "max_tokens": 1024
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return "❌ AI Answer parse nahi ho saka. Kripya punah prayas karein."
    except Exception as e:
        return "⚡ AI Engine abhi busy hai, kripya thodi der baad sawaal poochein."
