# News Site Extraction Patterns

Site-specific selectors and JavaScript extraction scripts for news aggregators and portals.

## Techmeme

- **Section**: `#topcol1`
- **Items**: `.item`
- **Headlines**: `strong > a`
- **Context pattern**: Text after `strong` up to source links, separated by `—`

### DOM-based extraction (recommended)
```javascript
(() => {
  const topcol = document.getElementById('topcol1');
  if (!topcol) return 'no topcol1';
  const strongLinks = topcol.querySelectorAll('strong a');
  const news = [];
  for (let link of strongLinks) {
    const headline = link.textContent.trim();
    let parent = link.parentElement;
    let context = '';
    while (parent && !context) {
      const text = parent.textContent;
      const dashIndex = text.indexOf('—');
      if (dashIndex !== -1) {
        context = text.substring(dashIndex + 1).trim().replace(/\s+/g, ' ').substring(0, 200);
      }
      parent = parent.parentElement;
    }
    news.push({ headline, context });
  }
  return news.slice(0, 3);
})()
```

### Text-based fallback (when DOM structure changes)
```javascript
(() => {
  const bodyText = document.body.innerText;
  const idx = bodyText.indexOf('Top News');
  if (idx === -1) return [];
  let after = bodyText.substring(idx, idx + 4000);
  after = after.replace(/\u00A0/g, ' ');
  const results = [];
  const sources = ['CNBC:', 'Apple:', 'Mark Gurman / Bloomberg:'];
  for (let source of sources) {
    const start = after.indexOf(source);
    if (start === -1) continue;
    let segment = after.substring(start);
    const nextMore = segment.indexOf('More:');
    if (nextMore !== -1) segment = segment.substring(0, nextMore);
    const dash = segment.indexOf('—');
    if (dash === -1) continue;
    let headline = segment.substring(source.length, dash).trim();
    let context = segment.substring(dash + 1).trim();
    headline = headline.replace(/\s+/g, ' ');
    context = context.replace(/\s+/g, ' ');
    if (context.length > 200) context = context.substring(0, 197) + '...';
    results.push({ headline, context });
  }
  return results.slice(0, 3);
})()
```

## Hacker News

- **Items**: `.athing`
- **Headlines**: `.titleline > a`
- **Context**: `.subtext` (points, user, time)

## Reddit

- **Items**: `[data-testid="post-container"]`
- **Headlines**: `h3`
- **Context**: `.text-neutral-content`

## General Workflow

```
web_extract (quick check) → browser_navigate (if complex)
browser_console (DOM exploration) → browser_console (extraction script)
browser_vision (fallback for visual confirmation)
```

1. Try `web_extract` first — fastest path for structured content
2. If content is truncated or confusing, use `browser_navigate`
3. Use `browser_console` to explore DOM structure and run extraction scripts
4. If DOM selectors fail, fall back to text-based pattern matching
5. For lazy-loaded pages, use `browser_scroll(direction='down')` before extracting

*Extracted from web-news-extraction skill (2026-04-11)*
