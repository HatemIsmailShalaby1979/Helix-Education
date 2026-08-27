# Marketing Assets — Helix Education Center V.2

This directory contains the marketing landing page and assets for the Helix Education Center V.2 release.

## Structure

```text
marketing/
├── index.html          # Dark-mode landing page
├── styles.css          # External stylesheet
├── architecture.mmd    # Mermaid architecture diagram source
└── README.md           # This file
```

## Quick Start

### View Locally

Open `index.html` directly in a browser, or serve with a local server:

```bash
# Python 3
python -m http.server 8080 -d marketing

# Node.js (npx)
npx serve marketing

# Then open http://localhost:8080
```

### Render Mermaid Diagram

The architecture diagram in `index.html` uses a `<pre class="mermaid">` block. To render it:

1. **Browser**: Include `mermaid.min.js` via CDN (already referenced in HTML)
2. **CLI**: `npx -p @mermaid-js/mermaid-cli mmdc -i architecture.mmd -o architecture.svg`
3. **VS Code**: Install "Markdown Preview Mermaid Support" extension

### Build for Production

```bash
# Install marketing dependencies
pip install -e ".[marketing]"

# Or manually
pip install jinja2 markdown mermaid-cli
```

## Customization

### Colors (CSS Custom Properties)

Edit `:root` in `index.html` `<style>` block:

```css
:root {
    --bg: #0a0f0d;           /* Page background */
    --accent: #00ff88;       /* Primary brand color */
    --accent-dim: #00cc6a;   /* Hover state */
    --card: #141d19;         /* Card backgrounds */
    --border: #1e2d26;       /* Subtle borders */
}
```

### Content Sections

| Section      | HTML ID            | Purpose                             |
|--------------|--------------------|-------------------------------------|
| Hero         | `#hero`            | Headline, CTAs, trust badges        |
| Features     | `#features`        | 4 key selling points                |
| Architecture | `#architecture`    | Mermaid diagram                     |
| Philosophy   | `#philosophy`      | 6 design principles                 |
| CTA          | `#cta`             | Final conversion                    |

### Adding Analytics

Add before `</head>`:

```html
<!-- Plausible -->
<script defer data-domain="helix.education" src="https://plausible.io/js/script.js"></script>

<!-- Or Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

## Deployment

### GitHub Pages

1. Push `marketing/` to `gh-pages` branch
2. Enable Pages in repo settings
3. Custom domain: `helix.education`

### Netlify/Vercel

```bash
# Netlify
npx netlify deploy --prod --dir=marketing

# Vercel
npx vercel --prod marketing
```

### Docker (nginx)

```dockerfile
FROM nginx:alpine
COPY marketing/ /usr/share/nginx/html/
EXPOSE 80
```

```bash
docker build -t helix-marketing .
docker run -p 8080:80 helix-marketing
```

## Accessibility Checklist

- [x] Semantic HTML5 landmarks
- [x] Skip link for keyboard users
- [x] Focus visible on all interactive elements
- [x] Color contrast ≥ 4.5:1 (WCAG AA)
- [x] Reduced motion respected
- [x] Alt text for decorative SVGs (aria-hidden)
- [x] Logical heading hierarchy
- [ ] Test with screen reader (NVDA/VoiceOver)
- [ ] Test keyboard-only navigation

## Performance

- No external CSS/JS dependencies (self-contained)
- System fonts with Google Fonts preconnect
- Mermaid loaded only when needed

- Target: < 100KB total, < 1s FCP on 3G

## License

MIT — Helix Education Center V.2 — Zero-AI, Event-Sourced, Yours.