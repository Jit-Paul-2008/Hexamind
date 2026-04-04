# Option C Key Setup

Provide these two values to enable full cloud fallback:

HUGGINGFACE_API_KEY=hf_your_token_here
OPENROUTER_API_KEY=sk-or-your_token_here

After setting them in your runtime env, restart backend:

sudo docker compose up -d --build backend

Then verify diagnostics include availability=true for both fallback layers.
