import httpx
from config import GROQ_API_KEY

async def get_ai_response(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "⚠️ Groq API Key configured nahi hai. Admin se check karne ko kahein."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Updated model: llama-3.1-8b-instant
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert Sarkari Exam Tutor. Answer accurately and clearly in simple Hindi/Hinglish."
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
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            data = res.json()
            
            if res.status_code == 200 and "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            elif "error" in data:
                return f"⚠️ API Error: {data['error'].get('message', 'Unknown error')}"
            else:
                return "❌ AI Answer generate nahi ho saka. Thodi der baad try karein."
    except Exception as e:
        return f"⚡ Request error: {str(e)}"
