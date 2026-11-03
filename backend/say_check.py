"""Ask the model to repeat what is said in a video.
Run from D:\\FixLens\\backend:
    python say_check.py D:\\FixLens\\spoken.mp4
"""
import base64
import sys
from pathlib import Path

from openai import OpenAI

from app.config import get_settings

path = Path(sys.argv[1])
s = get_settings()
client = OpenAI(api_key=s.baseten_api_key, base_url=s.baseten_base_url, timeout=120)
b64 = base64.b64encode(path.read_bytes()).decode()
r = client.chat.completions.create(
    model=s.baseten_model,
    max_tokens=3000,
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "Repeat word for word what the person says in this video. "
                                 "If you cannot hear any audio, reply exactly: NO AUDIO"},
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}},
    ]}],
)
print(r.choices[0].message.content)