export default {
  async fetch(request, env, ctx) {
    try {
      const url = new URL(request.url);
      let pathname = url.pathname;

      // Root / → index.html
      if (pathname === '/' || pathname === '') {
        pathname = '/index.html';
      }

      // Neue URL für die Datei
      const newUrl = new URL(pathname, request.url);

      // Versuche, die Datei zu laden
      const response = await getAsset(env, pathname);
      if (response) {
        return response;
      }

      return new Response('Not found', { status: 404 });
    } catch (e) {
      return new Response('Error: ' + e.message, { status: 500 });
    }
  }
};

async function getAsset(env, pathname) {
  // Die Assets werden über Wrangler automatisch in KV gespeichert
  try {
    if (env.ASSETS) {
      return env.ASSETS.fetch(new Request('http://assets' + pathname));
    }
  } catch (e) {
    // Fallback
  }
  return null;
}
