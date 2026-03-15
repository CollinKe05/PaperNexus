# PaperNexus Setup

## Install

```bash
pip install -r requirements.txt
```

## Configure optional APIs and recognizers

Copy `.env.example` to `.env` and set any keys you have:

- `OPENAI_API_KEY` for real LLM graph reconstruction
- `MATHPIX_APP_ID` and `MATHPIX_APP_KEY` for OCR on formula images
- `NOUGAT_ENABLED=true` and `NOUGAT_COMMAND=nougat` to enable Nougat formula extraction

If Nougat is enabled, make sure the `nougat` CLI is installed and available in `PATH`.

Without these optional components, the app still runs with semantic fallback parsing.

## Run

```bash
uvicorn backend.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).
