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
      const headers = new Headers(response.headers);
      headers.set('Content-Type', contentType);

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
