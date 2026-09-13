export default {
  async fetch(request, env) {
    // Versuche die statische Datei zu servieren
    let response;

    try {
      response = await env.ASSETS.fetch(request);
    } catch (e) {
      // Fallback wenn env.ASSETS nicht verfügbar
      return new Response('ASSETS binding not configured', { status: 500 });
    }

    if (!response) {
      return new Response('Not found', { status: 404 });
    }

    // Neuer Response mit modifizierten Headers
    const headers = new Headers(response.headers);

    // Entferne GitHub CSP
    headers.delete('Content-Security-Policy');
    headers.delete('content-security-policy');
    headers.delete('X-Content-Security-Policy');

    // Setze lockere CSP
    headers.set('Content-Security-Policy', "default-src *; style-src * 'unsafe-inline'; script-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; font-src * data:; connect-src *; frame-src *");

    // Security Headers
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('X-Frame-Options', 'SAMEORIGIN');
    headers.set('Cache-Control', 'public, max-age=3600');

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: headers
    });
  }
};
