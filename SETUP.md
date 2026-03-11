# PaperNexus Setup

## Install

```bash
pip install -r requirements.txt
```

## Configure optional APIs

Copy `.env.example` to `.env` and set any keys you have:

- `OPENAI_API_KEY` for real LLM graph reconstruction
- `MATHPIX_APP_ID` and `MATHPIX_APP_KEY` for OCR on formula images

Without these keys, the app still runs with heuristic fallbacks.

## Run

```bash
uvicorn backend.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).
