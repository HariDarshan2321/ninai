# Website deployment

## Recommended host: Vercel

Vercel is the best default for the current Ninai website because it supports Next.js
without an adapter, provides a preview URL for each pull request, accepts a custom domain
without moving the domain's nameservers, and leaves room for future non-static Next.js
features.

1. Create and push the intended public repository:

   ```bash
   git init
   git add .
   git commit -m "feat: launch Ninai MVP"
   gh repo create HariDarshan2321/ninai --public --source=. --remote=origin --push
   ```

2. Import the repository in Vercel.
3. Set the project root directory to `website`.
4. Keep the detected framework as Next.js and the build command as `npm run build`.
5. Deploy the generated preview and run the release checks below against its URL.
6. Add `ninai.io` and `www.ninai.io` in the Vercel project domain settings.
7. Add the DNS records Vercel provides in the current Spaceship DNS dashboard.
8. Make `ninai.io` canonical and redirect `www.ninai.io` to it.

Official references:

- <https://vercel.com/docs/frameworks/full-stack/nextjs>
- <https://vercel.com/docs/deployments/overview>
- <https://vercel.com/kb/guide/how-do-i-add-a-custom-domain-to-my-vercel-project>

## Alternative: GitHub Pages

The repository already includes `.github/workflows/pages.yml`. After the repository exists:

1. Open repository Settings, then Pages.
2. Select GitHub Actions as the publishing source.
3. Configure `ninai.io` as the custom domain before treating the project-site URL as a
   production preview; the export uses root-relative asset URLs for the custom domain.
4. Update the Spaceship DNS records using GitHub's current apex-domain instructions.
5. Enable HTTPS after DNS verification completes.

GitHub Pages is the lowest-complexity static option, but it does not provide the same
pull-request preview workflow as Vercel.

Official references:

- <https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>
- <https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site>

## Alternative: Cloudflare Pages

Cloudflare Pages can deploy the existing static export with these settings:

- Root directory: `website`
- Framework preset: Next.js (Static HTML Export)
- Build command: `npm run build`
- Build output directory: `out`

It provides preview deployments and a global CDN. Using `ninai.io` as an apex domain on
Cloudflare Pages requires adding the domain as a Cloudflare zone and moving its nameservers
from Spaceship to Cloudflare.

Official references:

- <https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/>
- <https://developers.cloudflare.com/pages/configuration/custom-domains/>

## Release checks

Run from `website/`:

```bash
npm ci
npm audit --audit-level=moderate
npm run typecheck
npm run build
python3 ../scripts/validate_website.py
```

Run from `engine/` with the project environment activated:

```bash
python -m unittest discover -s tests -v
```

The website validator checks required export files, metadata, unique titles and
descriptions, one H1 per public page, 404 noindex behavior, internal file references, and
anchor targets.

## Current blockers

- `https://github.com/HariDarshan2321/ninai` does not currently resolve publicly.
- The website's source links and install command intentionally use that URL, so the public
  repository must be created before the website is launched.
- `ninai.io` currently uses Spaceship nameservers and still resolves to parking endpoints;
  its DNS must be pointed to the selected host after a successful preview deployment.
