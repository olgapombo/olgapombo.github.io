**Yes — you can deploy a thin proxy Worker that fetches your site from GitHub Pages on every request.**

Create a new directory and add this `index.js`:

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Replace with your actual GitHub Pages URL
    const target = new URL(url.pathname + url.search, "https://olgapombo.github.io");

    const modifiedRequest = new Request(target, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    return fetch(modifiedRequest);
  }
};
```

Then deploy:

```bash
npx wrangler deploy
```

After deploy, add your custom domain in the Worker dashboard under **Triggers > Custom Domains**.

### Important considerations

- **Relative URLs** in your HTML/CSS should work fine since the browser sees the Cloudflare domain.
- **GitHub Pages may rate-limit** or block Cloudflare IPs if traffic is high.
- **Redirects** from GitHub Pages will point to `github.io` unless you rewrite headers.

### A simpler alternative

If you only need a Cloudflare domain pointing to GitHub Pages, you don't need a Worker at all:

1. In Cloudflare DNS, add a `CNAME` record for your domain pointing to `olgapombo.github.io`
2. Enable the orange cloud (proxied)
3. In your GitHub repo settings, add the same custom domain under **Pages**

This gives you Cloudflare caching, SSL, and your domain with zero code.

Would you like me to help you set up the DNS records, or do you prefer the Worker proxy approach?