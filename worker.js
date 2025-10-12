const BASE_URL = "https://example.workers.dev/checklist/"; // Python betiği bunu otomatik güncelleyecek

addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  };

  // === CORS preflight ===
  if (request.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  // === Proxy Mode ===
  if (path.startsWith("/proxy/")) {
    const target = decodeURIComponent(path.replace("/proxy/", ""));
    try {
      // Eğer hedef URL'de slash eksikse düzelt
      const fixedTarget = target.replace(/\.dev(?!\/)/, ".dev/");
      const res = await fetch(fixedTarget, { headers: { "Referer": BASE_URL } });

      if (!res.ok) {
        return new Response(`Proxy Fetch Error (${res.status})`, { status: res.status });
      }

      // Orijinal content-type'ı koru
      const contentType = res.headers.get("Content-Type") || "application/octet-stream";
      return new Response(res.body, {
        headers: { ...corsHeaders, "Content-Type": contentType },
      });
    } catch (err) {
      return new Response("Proxy Error: " + err, { status: 502 });
    }
  }

  // === Playlist Mode ===
  if (path.startsWith("/checklist/")) {
    const cid = path.split("/checklist/")[1];
    const playlistUrl = `${BASE_URL}${cid}`;

    try {
      const res = await fetch(playlistUrl);
      if (!res.ok) {
        return new Response(`Fetch Error (${res.status})`, { status: res.status });
      }

      let text = await res.text();

      // Slash eksik hatalarını düzelt: ".dev" sonrası '/' yoksa ekle
      text = text.replace(/\.dev(?!\/)/g, ".dev/");

      // Her URL'yi proxy altına encode ederek dönüştür
      text = text.replace(
        /(https?:\/\/[^\s\n]+)/g,
        (m) => `/proxy/${encodeURIComponent(m)}`
      );

      return new Response(text, {
        headers: { ...corsHeaders, "Content-Type": "application/vnd.apple.mpegurl" },
      });
    } catch (err) {
      return new Response("Fetch Error: " + err, { status: 500 });
    }
  }

  // === Varsayılan yanıt ===
  return new Response("Cloudflare Worker aktif 🚀", { headers: corsHeaders });
}
