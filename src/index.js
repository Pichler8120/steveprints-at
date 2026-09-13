export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let pathname = url.pathname;

    // Root / → index.html
    if (pathname === '/' || pathname === '') {
      pathname = '/index.html';
    }

    try {
      // Serve lokale assets via Cloudflare
      const assetResponse = await env.ASSETS.fetch(new Request(`http://assets${pathname}`, request));

      if (assetResponse.status === 404) {
        return assetResponse;
      }

      const headers = new Headers(assetResponse.headers);

      // Entferne restriktive CSP-Header
      headers.delete('Content-Security-Policy');
      headers.delete('X-Content-Security-Policy');
      headers.delete('content-security-policy');

      // Setze lockere CSP nur für HTML
      if (pathname.endsWith('.html')) {
        headers.set('Content-Security-Policy', "default-src *; style-src * 'unsafe-inline'; script-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; font-src * data:; connect-src *");
      }

      headers.set('X-Content-Type-Options', 'nosniff');
      headers.set('X-Frame-Options', 'SAMEORIGIN');
      headers.set('Cache-Control', 'public, max-age=3600');

      return new Response(assetResponse.body, {
        status: assetResponse.status,
        headers: headers
      });
    } catch (e) {
      return new Response('Error: ' + e.message, { status: 500 });
    }
  }
};
