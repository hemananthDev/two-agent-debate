import os
import re
import json
import sys
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Walk up from backend/ to find the .env file in the nearest parent that contains it
def find_env():
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(current, ".env")
        if os.path.exists(candidate):
            return current
        current = os.path.dirname(current)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = find_env()
load_dotenv(os.path.join(BASE_DIR, ".env"))

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("[error] GROQ_API_KEY not found in environment variables!")
    print(f"[debug] Looked in: {os.path.join(BASE_DIR, '.env')}")
    sys.exit(1)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Accept"],
)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    http_client=httpx.Client(verify=False)
)


class DebateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    turns: int = Field(ge=1, le=20)
    max_lines: int = Field(ge=1, le=50)
    agent1_model: str
    agent2_model: str
    judge_model: str
    agent1_name: str = Field(min_length=1, max_length=50)
    agent2_name: str = Field(min_length=1, max_length=50)
    judge_name: str = Field(min_length=1, max_length=50)


@app.get("/models")
def get_models():
    try:
        models = client.models.list()
        return {"models": [m.id for m in models.data]}
    except Exception as e:
        print(f"[error] Failed to fetch models from Groq: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Failed to fetch models from Groq: {str(e)}")


def chat(model, messages, turn, turns, max_lines):
    messages = messages.copy()
    messages[0] = {**messages[0], "content": messages[0]["content"] + f" This is turn {turn} of {turns}. You have {turns - turn} turn(s) remaining after this."}
    response = client.chat.completions.create(model=model, messages=messages)
    reply = response.choices[0].message.content
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
    lines = [line for line in reply.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def build_system_prompt(side, topic, your_name, opponent_name, turns, max_lines):
    return f"You are {your_name}, a debater arguing {side} the following topic: \"{topic}\". Your opponent's name is {opponent_name}. You have exactly {turns} turns in total. Each of your responses must not exceed {max_lines} lines. Speak naturally and directly — address {opponent_name} by name, use first-person language, and avoid robotic or formal phrases. Be concise, persuasive, and respond directly to {opponent_name}'s last point. Strategize knowing how many turns you have left. Do not re-introduce yourself."


def build_judge_system_prompt(judge_name):
    return f"You are {judge_name}, a strict and impartial debate judge. Your rulings are based solely on the logical strength, evidence, and persuasiveness of the arguments presented."


def judge_open(req):
    messages = [
        {"role": "system", "content": build_judge_system_prompt(req.judge_name)},
        {"role": "user", "content": f"Open the debate. Topic: \"{req.topic}\". Debaters: {req.agent1_name} (FOR) vs {req.agent2_name} (AGAINST). Rules: {req.turns} turns each, max {req.max_lines} lines per response. Introduce the topic and the debaters, state the rules clearly, and declare the debate open. Speak naturally as a judge addressing the room."}
    ]
    response = client.chat.completions.create(model=req.judge_model, messages=messages)
    return response.choices[0].message.content


def judge_verdict(req, transcript):
    messages = [
        {"role": "system", "content": build_judge_system_prompt(req.judge_name)},
        {"role": "user", "content": f"The debate has concluded. Here is the full transcript:\n\n{transcript}\n\nBased solely on the arguments made, deliver your verdict. Declare the winning side as either FOR or AGAINST — not by the debater's name. Explain why that side argued more effectively, referencing specific points made. Be impartial and decisive."}
    ]
    response = client.chat.completions.create(model=req.judge_model, messages=messages)
    return response.choices[0].message.content


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def save_debate(topic, transcript):
    filename = f"debate-{slugify(topic)}.md"
    path = os.path.join(BASE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Debate: {topic}\n\n")
        f.write(transcript)
    return filename


def stream_debate(req: DebateRequest):
    transcript = ""

    def event(kind, speaker, content):
        return f"data: {json.dumps({'type': kind, 'speaker': speaker, 'content': content})}\n\n"

    try:
        opening = judge_open(req)
        transcript += f"## Judge's Opening\n\n**{req.judge_name}:**\n{opening}\n\n"
        yield event("opening", req.judge_name, opening)

        agent1_messages = [{"role": "system", "content": build_system_prompt("FOR", req.topic, req.agent1_name, req.agent2_name, req.turns, req.max_lines)}]
        agent2_messages = [{"role": "system", "content": build_system_prompt("AGAINST", req.topic, req.agent2_name, req.agent1_name, req.turns, req.max_lines)}]

        for turn in range(1, req.turns + 1):
            yield event("turn_start", "", str(turn))

            reply1 = chat(req.agent1_model, agent1_messages, turn, req.turns, req.max_lines)
            agent1_messages.append({"role": "assistant", "content": reply1})
            agent2_messages.append({"role": "user", "content": reply1})
            transcript += f"## Turn {turn} of {req.turns}\n\n**{req.agent1_name} (FOR):**\n{reply1}\n\n"
            yield event("agent1", req.agent1_name, reply1)

            reply2 = chat(req.agent2_model, agent2_messages, turn, req.turns, req.max_lines)
            agent2_messages.append({"role": "assistant", "content": reply2})
            agent1_messages.append({"role": "user", "content": reply2})
            transcript += f"**{req.agent2_name} (AGAINST):**\n{reply2}\n\n"
            yield event("agent2", req.agent2_name, reply2)

        verdict = judge_verdict(req, transcript)
        transcript += f"## Judge's Verdict\n\n**{req.judge_name}:**\n{verdict}\n"
        yield event("verdict", req.judge_name, verdict)

        try:
            filename = save_debate(req.topic, transcript)
            yield event("saved", "", filename)
        except Exception as e:
            yield event("error", "", f"Debate completed but failed to save file: {str(e)}")

    except Exception as e:
        yield event("error", "", f"Debate error: {str(e)}")


@app.post("/debate")
def debate(req: DebateRequest):
    return StreamingResponse(stream_debate(req), media_type="text/event-stream")
