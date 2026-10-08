# BananaBooth

A personal, single-file UI for Google's Nano Banana image models, using either the **Gemini API** (Google) or **Replicate** as the provider. It's plain HTML/JS with no build step and no dependencies.

## Run

```sh
python3 server.py
```

Then open **http://localhost:8787**. You only need Python 3; nothing else to install.

`server.py` serves `index.html` and proxies Replicate calls, because `api.replicate.com` doesn't accept requests from browser pages. It listens on `127.0.0.1` only. Use `--port 9000` to change the port.

**Google only?** You can also open `index.html` directly from disk (`file://`) in Chrome. The Gemini API accepts browser requests, so the proxy isn't needed. Replicate won't work that way.

## Providers

| Provider  | Key                                                              | Models                                                   |
|-----------|------------------------------------------------------------------|----------------------------------------------------------|
| Google    | Gemini API key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `gemini-3.1-flash-image`, `gemini-3-pro-image`           |
| Replicate | API token: [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens) | `google/nano-banana-2`, `google/nano-banana-pro`         |

Each provider's key is stored separately in your browser's `localStorage`. Keys never touch the disk. The proxy passes the Replicate token through in the request header and never logs or stores it.

On Replicate, reference images are uploaded through the Files API and passed as `image_input`. For Nano Banana Pro, `allow_fallback_model` is always `false`, so you never quietly get a different model.

## Data

- **History:** every result (the full image plus a preview) is kept in the browser's IndexedDB. Pages served from `localhost:8787` and pages opened via `file://` have **separate** histories.
- **Save to folder** (Chrome/Edge): automatically writes each image and a `.txt` file with its prompt and settings into a folder you pick.
- **Costs** are estimates based on the price constants at the top of the script in `index.html`. Check them against [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) and the Replicate model pages.

## Security

Don't host `index.html` publicly, and don't expose `server.py` beyond localhost. Both are made for one person running them on their own machine.
