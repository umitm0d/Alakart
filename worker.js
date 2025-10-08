const BASE_URL = "https://example.workers.dev/checklist/";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // Proxy endpoint
    if (path.startsWith("/proxy/")) {
      const target = decodeURIComponent(path.replace("/proxy/", ""));
      try {
        const res = await fetch(target, { headers: { "Referer": BASE_URL } });
        return new Response(res.body, {
          headers: { ...corsHeaders, "Content-Type": res.headers.get("Content-Type") },
        });
      } catch (err) {
        return new Response("Proxy Error: " + err, { status: 502 });
      }
    }

    // Playlist endpoint
    if (path.startsWith("/checklist/")) {
      const cid = path.split("/checklist/")[1];
      const playlist = `${BASE_URL}${cid}`;
      try {
        const res = await fetch(playlist);
        let text = await res.text();
        text = text.replace(/(https:\/\/[^ \n]+)/g, (m) => `/proxy/${encodeURIComponent(m)}`);
        return new Response(text, {
          headers: { ...corsHeaders, "Content-Type": "application/vnd.apple.mpegurl" },
        });
      } catch (err) {
        return new Response("Fetch Error: " + err, { status: 500 });
      }
    }

    return new Response("Cloudflare Worker aktif 🚀", { headers: corsHeaders });
  },
};
