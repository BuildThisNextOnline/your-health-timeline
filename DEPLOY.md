# Deploying to GitHub Pages

The site is a static folder (`site/`) that contains **only encrypted data**. Hosting
it publicly is safe as long as you never commit the plaintext in `data/` or
`reports/`, or the `data/passphrases.json` file. The included `.gitignore` already
blocks these — don't override it.

## One-time setup

1. **Build** so `site/data/*.enc` and `manifest.json` are up to date:
   ```bash
   python scripts/build.py
   ```
2. **Create a repository** and push. From the project root:
   ```bash
   git init
   git add .
   git commit -m "Health history dashboard (encrypted data only)"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. **Before the first push, sanity-check what will be public** — this must list
   only `.enc` and `manifest.json` under `site/data`, and must NOT list
   `passphrases.json`, `data/structured`, `data/payload`, or `reports`:
   ```bash
   git ls-files | grep -E "data/|reports/|passphrase" 
   ```
   Expected output: just `site/data/*.enc` and `site/data/manifest.json`.
4. **Enable Pages**: GitHub repo → Settings → Pages → Source: *Deploy from a branch*
   → Branch `main`, folder `/root`… but Pages serves the repo root, so either:
   - set the Pages folder to `/site` is not offered for branch deploys, so the
     simplest options are:
     - **(a)** move the contents of `site/` to the repo root, or
     - **(b)** add a GitHub Actions Pages workflow that publishes the `site/`
       folder (recommended — keeps the repo tidy).

### Option (b): Actions workflow (recommended)

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy site
on:
  push: { branches: [main] }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deploy.outputs.page_url }}" }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
      - id: deploy
        uses: actions/deploy-pages@v4
```

Then in Settings → Pages, set Source to **GitHub Actions**. Your site publishes at
`https://<you>.github.io/<repo>/`.

## Sharing with people

Give each person their URL + **their own passphrase** (from
`data/passphrases.json`) through a private channel (not in the repo, not in chat
logs you wouldn't want shared). They pick their name and unlock only their data.

You can change any passphrase: edit `data/passphrases.json`, then re-run
`python scripts/build.py` to re-encrypt, and push.

## Updating data later

Add reports to `reports_manifest.py`, run `python scripts/build.py`, commit, push.
Only the `.enc` blobs change; passphrases stay the same unless you edit them.

## A note on strength

A passphrase on a public ciphertext can, in principle, be attacked offline. The
generated 6-word + number passphrases with 600k PBKDF2 iterations are a solid
default, but for maximum protection you can set longer custom passphrases in
`data/passphrases.json` before building, or keep the repo **private** and still
use the same per-person unlock.
