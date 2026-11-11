# Deployment guide

This guide puts the assistant on the internet so you can link to a live demo from
your CV or GitHub profile. It covers four hosts, from easiest to most self-reliant:

| Option | Cost | Models | Best for |
|---|---|---|---|
| **Vercel** | Free (Hobby) | Cloud API (Gemini, Groq, OpenAI) | A fast, always-on demo link |
| **Render** | Free tier (sleeps when idle) | Cloud API | A Docker deployment with almost no setup |
| **Railway** | Usage-based, small monthly credit | Cloud API | Docker with no sleeping |
| **Your own VPS** | About $10 to $30 a month | Ollama on the server, fully private | Showing a fully self-hosted stack |

## Why not Ollama on Vercel?

Vercel runs your code as short-lived serverless functions. There is no GPU, no
long-running process and no room for a 5 GB model, so Ollama cannot run there.
The app is built for this. Set `LLM_PROVIDER=openai` and `EMBED_PROVIDER=openai`
and the same code calls a hosted model instead. The vector database also has to
live outside the function, which is what Qdrant Cloud is for.

If you specifically want to show local models, use the VPS option at the end.

---

## Step 1: Create the cloud services (all free, no card needed)

### Qdrant Cloud (vector database)

1. Sign up at https://cloud.qdrant.io and create a **Free** cluster. Choose a region close to where the app will run (for example `eu-central` for Frankfurt, or a US East region to sit near Vercel's default `iad1`).
2. When the cluster is ready, copy its **URL** (it looks like `https://abc123.eu-central-1-0.aws.cloud.qdrant.io`) and create an **API key**.

The free cluster (1 GB RAM, 4 GB disk) holds this knowledge base hundreds of times over. Free clusters are suspended after a long period without traffic; if your demo stops finding anything, open the Qdrant dashboard and resume the cluster.

### Google Gemini (chat and embeddings)

1. Go to https://aistudio.google.com/apikey and create an API key.
2. In AI Studio, check which **Flash** model is current. Google renames models often; `gemini-2.5-flash` is used in the examples below, but any current Flash or Flash-Lite model works.

One key covers both the chat model and the embedding model (`gemini-embedding-001`), through Google's OpenAI-compatible endpoint.

**Optional: Groq for faster answers.** Create a key at https://console.groq.com and use it for chat only (keep Gemini for embeddings, because Groq doesn't offer them). Use a model that is listed as current in Groq's model list, such as `openai/gpt-oss-20b`. Groq retired `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` for free accounts in August 2026, so older tutorials that use them will fail.

---

## Step 2: Index the knowledge base into Qdrant Cloud (from your computer)

Ingestion runs once, from your machine, straight into the cloud cluster. The
deployed app only reads from it.

Create `.env` (it is git-ignored, so your keys stay private):

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=your-gemini-key
LLM_MODEL=gemini-2.5-flash

EMBED_PROVIDER=openai
EMBED_MODEL=gemini-embedding-001

QDRANT_URL=https://your-cluster-url.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-key
```

Then run:

```bash
python -m app.ingest
uvicorn app.main:app --reload     # optional: test against the cloud services locally
```

You should see `Stored 156 vectors (3072 dims) in collection 'knowledge_base'`.

> **The embedding model must be the same at ingestion time and at question time.**
> If you index with `gemini-embedding-001`, the deployed app must also use
> `gemini-embedding-001`. If you change it later, run ingestion again.

---

## Option A: Vercel

Vercel detects FastAPI automatically. `pyproject.toml` already tells it where the app is:

```toml
[tool.vercel]
entrypoint = "app.main:app"
```

### Deploy from the dashboard

1. Push the project to GitHub. Make sure `.env` is **not** committed (`git status` should not list it).
2. In Vercel, choose **Add New > Project** and import the repository. Leave the framework preset, build command and output directory at their defaults.
3. Open **Environment Variables** and add the variables from your `.env`. Mark the keys as sensitive:

   | Name | Value |
   |---|---|
   | `LLM_PROVIDER` | `openai` |
   | `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` |
   | `LLM_API_KEY` | your Gemini key |
   | `LLM_MODEL` | `gemini-2.5-flash` |
   | `EMBED_PROVIDER` | `openai` |
   | `EMBED_MODEL` | `gemini-embedding-001` |
   | `QDRANT_URL` | your cluster URL |
   | `QDRANT_API_KEY` | your Qdrant key |
   | `RATE_LIMIT_PER_MINUTE` | `20` |

4. Click **Deploy**. The first build takes one to two minutes.

### Or deploy from the command line

```bash
npm install -g vercel
vercel login
vercel                  # creates the project and a preview deployment
vercel env add LLM_API_KEY      # repeat for each variable above
vercel --prod           # production deployment
```

### Check that it works

```bash
curl https://your-project.vercel.app/api/health
```

Look for `"ready": true` and `"chunks": 156`. Then open the site and ask a question.

### Notes for Vercel

- **Region.** Functions run in Washington, D.C. (`iad1`) by default. If your Qdrant cluster is in Europe, change the function region in **Project Settings > Functions** to one close to it, which removes about 100 ms per question.
- **Streaming** works out of the box: answers appear token by token.
- **Rate limiting** is counted per function instance, so it slows down casual abuse but is not a hard limit. Set a spend cap or a low quota on your Gemini and Groq keys so a misbehaving visitor can't run up a bill.
- **Cold starts.** The first request after a quiet period takes a second or two longer while Python starts.
- **Embedded Qdrant (`QDRANT_PATH`) does not work on Vercel.** The file system is read-only and temporary. Always use Qdrant Cloud there.

---

## Option B: Render (Docker)

`render.yaml` describes the service, so Render can set it up from the repository.

1. Push the project to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render asks for the values marked `sync: false`: `LLM_API_KEY`, `QDRANT_URL` and `QDRANT_API_KEY`. Paste them in.
4. Apply the blueprint. Render builds the Docker image and gives you an `onrender.com` URL.

The free plan sleeps after 15 minutes without traffic, and the first visit after that takes about a minute to wake up. Upgrade to a paid instance if you want it always on.

## Option C: Railway (Docker)

1. In Railway, choose **New Project > Deploy from GitHub repo**. It finds the `Dockerfile` automatically.
2. Add the same environment variables as in the Vercel table under **Variables**.
3. Under **Settings > Networking**, click **Generate Domain**.

The Dockerfile reads the `PORT` variable that Railway and Render provide.

---

## Option D: Your own server with local models (fully self-hosted)

This keeps everything on one machine: Ollama, Qdrant and the app, with no external
APIs. It is the best way to show the "local" part of the project.

**Server size.** For `qwen3:8b` you need at least 8 GB of RAM (16 GB is comfortable) and 4 vCPUs. CPU-only answers take 10 to 30 seconds; a smaller model such as `qwen3:4b` or `llama3.2:3b` is noticeably faster. A GPU server makes answers near-instant but costs more.

### 1. Install Docker and get the code

On a fresh Ubuntu 24.04 server:

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Start everything, including Ollama

```bash
cp .env.example .env
# in .env set:  OLLAMA_BASE_URL_DOCKER=http://ollama:11434
docker compose --profile ollama up -d --build

docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama pull nomic-embed-text
docker compose run --rm app python -m app.ingest
```

Check it with `curl localhost:8000/api/health`.

### 3. Add HTTPS with a domain

Point a DNS `A` record (for example `assistant.yourdomain.com`) at the server's IP, then install Caddy, which obtains and renews certificates automatically:

```bash
sudo apt install -y caddy
echo 'assistant.yourdomain.com {
    reverse_proxy localhost:8000
}' | sudo tee /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Finally, close the other ports so only Caddy is reachable: `sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`. Docker publishes ports past `ufw`, so also change the port mappings in `docker-compose.yml` to `127.0.0.1:8000:8000`, `127.0.0.1:6333:6333` and `127.0.0.1:11434:11434`, then run `docker compose --profile ollama up -d` again.

---

## Updating the knowledge base after deployment

1. Edit or add files in `knowledge_base/`.
2. With your cloud `.env` active, run `python -m app.ingest`. It rebuilds the collection in Qdrant Cloud.
3. The live site picks up the new content immediately; no redeploy is needed. Commit the document changes so the repository stays in sync.

On the VPS, run `git pull` and then `docker compose run --rm app python -m app.ingest`.

## Security checklist

- [ ] `.env` is in `.gitignore` and was never committed. If a key ever was, revoke it and create a new one; deleting the file from Git history is not enough.
- [ ] API keys are stored as environment variables on the host, never in front-end code.
- [ ] `CORS_ORIGINS` is set to your site's URL if you don't need other sites to call the API.
- [ ] `RATE_LIMIT_PER_MINUTE` is set, and your Gemini and Groq keys have quotas or spend caps.
- [ ] Qdrant Cloud is protected by its API key (it is by default), and a self-hosted Qdrant is not exposed to the internet.

## Troubleshooting deployments

| Symptom | Cause and fix |
|---|---|
| `/api/health` shows `"ready": false` and `chunks: 0` | Ingestion went to a different Qdrant. Check that `QDRANT_URL` is the same locally and on the host, then re-run ingestion. |
| `"status": "degraded"` with "Vector database unreachable" | Wrong `QDRANT_URL` or `QDRANT_API_KEY`, or the free cluster was suspended. Resume it in the Qdrant dashboard. |
| Every answer says the documents don't cover the question | The embedding model on the host differs from the one used for ingestion, or `MIN_SCORE` is too high for that model. |
| "LLM API error (404)" | The model name is no longer offered. Pick a current model from the provider's list and update `LLM_MODEL`. |
| "LLM API error (429)" | You hit the provider's free-tier rate limit. Wait, lower traffic, or add billing. |
| Vercel build fails while installing packages | Make sure `requirements.txt` and `pyproject.toml` are both committed and list the same dependencies. |
| The page loads but answers never appear on a custom proxy | The proxy is buffering Server-Sent Events. Disable buffering for `/api/chat/stream` (Caddy and Vercel don't need changes). |
