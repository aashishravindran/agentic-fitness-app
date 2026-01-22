# Gemini Setup Guide

The Trainer Agent now uses **Google Gemini** as the default LLM (instead of OpenAI).

## Quick Setup

### 1. Get a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Set the API Key

```bash
# Option A: Environment variable (recommended)
export GOOGLE_API_KEY="your-api-key-here"

# Option B: Alternative name (also works)
export GEMINI_API_KEY="your-api-key-here"

# Option C: Add to .env file (if using python-dotenv)
echo "GOOGLE_API_KEY=your-api-key-here" >> .env
```

### 3. Optional: Choose Model

```bash
# Default: gemini-pro (stable, widely available)
# Alternative: gemini-1.5-flash (faster, newer)
# Note: gemini-1.5-pro may not be available in all API versions
export GEMINI_MODEL="gemini-pro"  # or "gemini-1.5-flash"
```

### 4. Test It

```bash
# Make sure data is ingested
python main.py ingest

# Test the trainer
python main.py train --fatigue "legs:0.8,push:0.2"
```

## Model Priority

The trainer will use models in this order:

1. **Gemini** (if `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set) ← **Default**
2. **OpenAI** (if `OPENAI_API_KEY` is set)
3. **Ollama** (local, if no API keys are set)

## Why Gemini?

- **Free tier available** (generous limits)
- **Fast responses** (especially `gemini-1.5-flash`)
- **Good structured output** support
- **No credit card required** for basic usage

## Troubleshooting

### "No module named 'pydantic_ai.models.google'"

Install the Google extra:
```bash
pip install pydantic-ai[google]
```

Or install the Google Generative AI package:
```bash
pip install google-generativeai
```

### "Invalid API key"

- Make sure you copied the full API key
- Check that `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set: `echo $GOOGLE_API_KEY`
- Verify the key is active in [Google AI Studio](https://makersuite.google.com/app/apikey)

### "Model not found" (404 error)

If you see a 404 error for model names, try:

1. **Check your API key type**: Some API keys only work with specific models
2. **Try different model names**:
   ```bash
   export GEMINI_MODEL="gemini-1.5-flash"  # Most compatible
   # or
   export GEMINI_MODEL="gemini-1.5-pro"
   # or
   GEMINI_MODEL=gemini-3-flash-preview
   ```
3. **The code will auto-try multiple models** - it will attempt:
   - Your specified model
   - `gemini-1.5-flash` (fast, widely available)
   - `gemini-1.5-pro` (more capable)
   - `gemini-1.0-pro` (older stable)
   - `gemini-pro` (legacy)

4. **Check available models**: Visit https://ai.google.dev/models/gemini to see what's available for your API key

## Fallback Options

If Gemini doesn't work, you can still use:

- **OpenAI**: Set `OPENAI_API_KEY`
- **Ollama**: Run `ollama serve` and pull a model

The trainer will automatically fall back to these if Gemini isn't available.
