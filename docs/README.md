# Project Lerna documentation site

This folder is a [VitePress](https://vitepress.dev/) site that presents the same material as the root `README.md`, `AGENTS.md`, and layer-specific READMEs—with search, sidebar navigation, and a home page.

## Commands

```bash
cd docs
npm install
npm run dev      # local dev server
npm run build    # static output to .vitepress/dist
npm run preview  # preview the production build
```

The dev server URL is printed in the terminal (often `http://localhost:5173`).

## Deploying the static site

After `npm run build`, upload the contents of `docs/.vitepress/dist` to any static host (GitHub Pages, Netlify, S3, and so on). Configure the host to serve `index.html` for unknown paths if you use clean URLs.
