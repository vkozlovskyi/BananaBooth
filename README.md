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

**Reference order:** each reference thumbnail has a number badge. Drag the thumbnails to reorder them. Refer to them in the prompt as "image 1", "image 2"… On Google, each image is sent right after a text part `Image N:`, and the prompt comes last. On Replicate, `image_input` follows the same order.

## Upscale (Topaz via Replicate)

Switch the left panel to **Upscale** to enlarge one photo with Topaz Labs' [`topazlabs/image-upscale`](https://replicate.com/topazlabs/image-upscale) on Replicate. It uses the same Replicate token, so it needs `server.py`.

- Drop, paste or pick a JPG, PNG or WebP photo, then choose **2x / 4x / 6x** and a model: Standard V2, High Fidelity V2, Low Resolution V2 or CGI. Face enhancement is optional; its Strength and Creativity are only sent when it's on.
- The output keeps the input's format (JPG stays JPG, anything else becomes PNG). `subject_detection` is always `None`.
- **Cost** depends on output megapixels: the first tier at or above the output MP, from $0.05 (≤ 24 MP) to $0.82 (≤ 512 MP). A factor that would exceed 512 MP is disabled.
- The result opens in a **before/after viewer**. Drag the divider, switch between Fit and 100%, and drag to pan. **Download** gives Replicate's file byte for byte. The result and the source photo are both kept in history; click the card's image to compare again.
- The uploaded photo is deleted from Replicate after each run, including after a failure or a cancel.

## Data

- **History:** every result (the full image plus a preview) is kept in the browser's IndexedDB. Pages served from `localhost:8787` and pages opened via `file://` have **separate** histories.
- **Save to folder** (Chrome/Edge): automatically writes each image and a `.txt` file with its prompt and settings into a folder you pick.
- **Costs** are estimates based on the price constants at the top of the script in `index.html`. Check them against [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) and the Replicate model pages.

## Security

Don't host `index.html` publicly, and don't expose `server.py` beyond localhost. Both are made for one person running them on their own machine.
