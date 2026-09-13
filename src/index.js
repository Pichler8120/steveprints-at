export default {
  async fetch(request) {
    const url = new URL(request.url);
    let pathname = url.pathname;

    // Root / → index.html
    if (pathname === '/' || pathname === '') {
      pathname = '/index.html';
    }

    // Fetch vom GitHub Repository
    const ghUrl = `https://raw.githubusercontent.com/Pichler8120/steveprints-at/main${pathname}`;

    try {
      const response = await fetch(ghUrl);

      if (response.status === 404) {
        return new Response('Not found', { status: 404 });
      }

      // Content-Type setzen
      const contentType = getContentType(pathname);
      const headers = new Headers();
      headers.set('Content-Type', contentType);

      // Entferne restriktive CSP-Header von GitHub
      headers.delete('Content-Security-Policy');
      headers.delete('X-Content-Security-Policy');

      // Setze lockere CSP für modernes Webdesign
      headers.set('Content-Security-Policy', "default-src *; style-src * 'unsafe-inline'; script-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; font-src * data:; connect-src *");
      headers.set('X-Content-Type-Options', 'nosniff');
      headers.set('X-Frame-Options', 'SAMEORIGIN');
      headers.set('Cache-Control', 'public, max-age=60');

      // Wenn es HTML ist: Body modifizieren um CSP-Meta-Tags zu entfernen
      if (pathname.endsWith('.html')) {
        const htmlText = await response.text();

        // Entferne CSP-Meta-Tags aus dem HTML
        const cleanedHtml = htmlText
          .replace(/<meta\s+http-equiv=['"]*Content-Security-Policy['"]*[^>]*>/gi, '')
          .replace(/<meta\s+content=[^>]*http-equiv=['"]*Content-Security-Policy['"]*[^>]*>/gi, '');

        return new Response(cleanedHtml, {
          status: response.status,
          headers: headers
        });
      }

      return new Response(response.body, {
        status: response.status,
        headers: headers
      });
    } catch (e) {
      return new Response('Error: ' + e.message, { status: 500 });
    }
  }
};

function getContentType(pathname) {
  if (pathname.endsWith('.html')) return 'text/html; charset=utf-8';
  if (pathname.endsWith('.css')) return 'text/css';
  if (pathname.endsWith('.js')) return 'application/javascript';
  if (pathname.endsWith('.json')) return 'application/json';
  if (pathname.endsWith('.svg')) return 'image/svg+xml';
  if (pathname.endsWith('.png')) return 'image/png';
  if (pathname.endsWith('.jpg') || pathname.endsWith('.jpeg')) return 'image/jpeg';
  if (pathname.endsWith('.gif')) return 'image/gif';
  if (pathname.endsWith('.txt')) return 'text/plain';
  return 'application/octet-stream';
}
