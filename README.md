# Two-Agent Debate

An AI-powered debate system where two LLMs argue opposing sides of a topic, moderated by a third LLM acting as an impartial judge. Built with FastAPI, plain HTML/CSS/JS, and powered by the Groq API.

---

## How It Works

1. The **Judge** opens the debate by introducing the topic, debaters, and rules
2. **Agent 1** argues FOR the topic
3. **Agent 2** argues AGAINST the topic
4. Agents alternate for the configured number of turns, each aware of their remaining turns
5. The **Judge** delivers a final verdict declaring the winning side (FOR or AGAINST) based solely on argument quality
6. The full debate is saved as a `.md` file in the project root

---

## Project Structure

```
two-agent-debate/
├── backend/
│   └── main.py        # FastAPI backend — model fetching, debate logic, SSE streaming
├── frontend/
│   ├── index.html     # UI layout
│   ├── style.css      # Styling
│   ├── app.js         # Model loading, form handling, SSE rendering
│   ├── server.js      # Express static file server
│   └── package.json
├── run.py             # Starts both backend and frontend
└── README.md
```

> The `.env` file lives one level up in the parent directory (`POC's/`) and is referenced automatically.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com/)

---

## Setup

### 1. Environment Variable

Create a `.env` file in the **parent directory** (`POC's/`):

```
GROQ_API_KEY=your_api_key_here
```

### 2. Install Python Dependencies

```bash
pip install fastapi uvicorn openai httpx python-dotenv
```

> **Note:** `httpx` is used with SSL verification disabled (`verify=False`) due to a known issue with corporate proxies or firewalls that intercept HTTPS traffic using a self-signed certificate. This is safe for local development.

### 3. Install Node Dependencies

```bash
cd frontend
npm install
```

---

## Running the Project

From the `two-agent-debate/` directory:

```bash
python run.py
```

This starts both servers in a single terminal:

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:3000 |
| Backend  | http://localhost:8000 |

Press `Ctrl+C` to stop both servers cleanly.

---

## Using the UI

1. Open `http://localhost:3000` in your browser
2. Enter a debate topic
3. Set the number of turns (how many times each agent speaks)
4. Set the max lines per response (hard-enforced)
5. Select a model and name for Agent 1 (FOR), Agent 2 (AGAINST), and the Judge from the live Groq model list
6. Click **Start Debate** — turns stream in one by one as they complete
7. The judge's verdict and a saved `.md` file path are shown at the end

---

## Configuration

Default model selections are pre-set in the UI dropdowns but can be changed at runtime:

| Agent    | Default Model                                |
|----------|----------------------------------------------|
| Agent 1  | `llama-3.3-70b-versatile`                    |
| Agent 2  | `qwen/qwen3-32b`                             |
| Judge    | `meta-llama/llama-4-scout-17b-16e-instruct`  |

All available models are fetched live from Groq on page load. To change defaults, update the `defaults` array in `frontend/app.js`.

---

## Output

Debate transcripts are saved as Markdown files in the `POC's/` directory:

```
debate-<topic-slug>.md
```

Each file contains the judge's opening, all turns, and the final verdict.
