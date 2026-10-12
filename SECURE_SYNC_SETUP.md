# Secure private recording sync — deployment plan

Status: NOT DEPLOYED. This file documents the required secure infrastructure; the current public GitHub Pages site does not upload JSON or audio to GitHub.

## Storage
- Public repository `mukul003/phrase-studio`: application source only. Never commit recordings or credentials.
- Create **private** repository `mukul003/phrase-studio-recordings` for recordings.
- Per session: `sessions/<full-session-uuid>/timing.json`, `audio-original.m4a`, and `manifest.json`.
- Each manifest includes short spoken code, full UUID, SHA-256 of both files, uploaded timestamp and source filename.
- Avoid identifiers based only on four digits; collisions are possible.
- Voice Memos recording must be selected explicitly by the user via the iOS Files picker; browser apps cannot read recordings directly from Voice Memos.

## Authentication architecture
- GitHub Pages contains NO GitHub token, client secret, private key, or long-lived credential.
- HTTPS authenticated API hosted separately (e.g. Cloudflare Worker).
- Authentication via Cloudflare Access with verified JWT/approved account. The Worker must verify JWT signature, issuer, audience, expiration and deny unauthorized requests; do not trust unverified identity headers.
- GitHub App installed only on the private recordings repository, with **Contents: Read and write** permission and minimal other permissions. Store private key and installation ID as Worker secrets only.
- Backend generates short-lived installation access tokens; never sends them to browser. Use strict allowlist of repository and paths, file types, sizes, SHA-256, rate limits, unique session IDs.
- Treat JSON as untrusted data; validate against schema. Never accept arbitrary repository paths or arbitrary URLs from the client.

## Transfer
1. User opens Voice Memos companion on iPhone, authenticates to private upload backend.
2. Recording session JSON is checkpointed to backend on tap Next (authenticated HTTPS; retries and acknowledgement). Local in-memory copy protects navigation, but persistent browser data is not needed after server acknowledgements.
3. User exports original M4A from Voice Memos to Files and selects it in the companion page's file picker (or share sheet after a future native extension).
4. Upload M4A to backend. Backend writes into correct private GitHub session folder, hashes and verifies contents before marking complete.
5. At home Windows imports by session UUID / spoken code. Audio alignment checks spoken marker and timestamps; code match alone is insufficient for synchronization.
6. A JSON backup download and a manual emergency export remain available.

## GitHub audio caveats
- Keep individual files under GitHub's 100 MB repository Contents API limit, preferably well below 20 MB for this Worker approach.
- Frequent recordings in Git history can grow storage significantly and deletion from the current tree does not purge historical blobs.
- GitHub repositories are not ideal long-term media stores; add retention/archive policy later.
- Do not use public GitHub issues, Pages, releases or workflows to carry private audio.

## Data minimization
- Disable persistent localStorage/IndexedDB for timing sessions ONLY AFTER successful server synchronization and testing.
- Offer delete-existing-local-data control, with separate confirmation, and verify remote manifest before clearing.
- Browser cache and site storage are distinct. HTTP caching may store the website source, but app must set no-store on authenticated upload responses.
- Never claim existing locally saved sessions have disappeared merely because app code changed.

## Deployment prerequisites — owner action required
1. Create the private recordings repository in GitHub.
2. Set up a GitHub App, install it only on that repository, and provide its App ID / installation ID to the secure backend (not in chat).
3. Create a Cloudflare account and Access-protected Worker; enter private signing key via Worker secret management only.
4. Deploy, verify authentication and upload/download test with dummy files before switching away from local persistence.

Never embed secrets in the public GitHub Pages source or paste private keys, tokens, or passwords into ChatGPT.
