const fetch = require('node-fetch');
const fs = require('fs');
const crypto = require('crypto');

const VT_API_KEY = process.env.VT_API_KEY;
const APPS_JSON_URL = process.env.APPS_JSON_URL; // artık koda gömülü değil, secret'tan geliyor
const OUTPUT_FILE = 'vt-scan-results.json';
const DELAY_MS = 16000; // dakikada 4 istek limiti için ~16sn ara (ücretsiz key)


const TEST_LIMIT = process.env.TEST_LIMIT ? parseInt(process.env.TEST_LIMIT, 10) : null;

if (!APPS_JSON_URL) {
  console.error('HATA: APPS_JSON_URL ortam değişkeni tanımlı değil.');
  console.error('Kullanım: APPS_JSON_URL=https://... VT_API_KEY=xxx node vt-scan-apks.js');
  process.exit(1);
}

if (!VT_API_KEY) {
  console.error('HATA: VT_API_KEY ortam değişkeni tanımlı değil.');
  console.error('Kullanım: VT_API_KEY=senin_anahtarin node vt-scan-apks.js');
  process.exit(1);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function downloadFile(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`İndirme başarısız (${res.status}): ${url}`);
  const buffer = await res.buffer();
  return buffer;
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

// Önce hash ile VT'de daha önce taranmış mı diye bak (yükleme yapmadan, kota harcamadan)
async function checkExistingReport(hash) {
  const res = await fetch(`https://www.virustotal.com/api/v3/files/${hash}`, {
    headers: { 'x-apikey': VT_API_KEY },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`VT rapor sorgusu başarısız: ${res.status}`);
  const json = await res.json();
  return summarize(json.data);
}

const LARGE_FILE_THRESHOLD = 32 * 1024 * 1024; // 32MB — VT üstü için özel upload URL istiyor

async function getUploadUrl() {
  const res = await fetch('https://www.virustotal.com/api/v3/files/upload_url', {
    headers: { 'x-apikey': VT_API_KEY },
  });
  if (!res.ok) throw new Error(`VT upload_url alınamadı: ${res.status}`);
  const json = await res.json();
  return json.data; // özel yükleme URL'si
}

async function uploadAndScan(buffer, filename) {
  const FormData = require('form-data');
  const form = new FormData();
  form.append('file', buffer, filename);

  // 32MB'den büyük dosyalar standart /files endpoint'ini kabul etmiyor (413 hatası verir),
  // bunlar için önce özel bir yükleme URL'si almamız gerekiyor.
  const targetUrl = buffer.length > LARGE_FILE_THRESHOLD
    ? await getUploadUrl()
    : 'https://www.virustotal.com/api/v3/files';

  if (buffer.length > LARGE_FILE_THRESHOLD) {
    console.log(`  dosya ${(buffer.length / 1024 / 1024).toFixed(1)}MB, büyük dosya yükleme URL'si kullanılıyor...`);
  }

  const uploadRes = await fetch(targetUrl, {
    method: 'POST',
    headers: { 'x-apikey': VT_API_KEY },
    body: form,
  });
  if (!uploadRes.ok) throw new Error(`VT yükleme başarısız: ${uploadRes.status}`);
  const uploadJson = await uploadRes.json();
  const analysisId = uploadJson.data.id;

  // Analiz tamamlanana kadar bekleyip sorgula
  let status = 'queued';
  let analysisData;
  while (status !== 'completed') {
    await sleep(15000);
    const analysisRes = await fetch(`https://www.virustotal.com/api/v3/analyses/${analysisId}`, {
      headers: { 'x-apikey': VT_API_KEY },
    });
    analysisData = await analysisRes.json();
    status = analysisData.data.attributes.status;
    console.log(`  ...analiz durumu: ${status}`);
  }

  const stats = analysisData.data.attributes.stats;
  return {
    malicious: stats.malicious,
    suspicious: stats.suspicious,
    harmless: stats.harmless,
    undetected: stats.undetected,
    total: stats.malicious + stats.suspicious + stats.harmless + stats.undetected,
    scanDate: new Date().toISOString(),
  };
}

function summarize(fileData) {
  const stats = fileData.attributes.last_analysis_stats;
  return {
    malicious: stats.malicious,
    suspicious: stats.suspicious,
    harmless: stats.harmless,
    undetected: stats.undetected,
    total: stats.malicious + stats.suspicious + stats.harmless + stats.undetected,
    scanDate: new Date(fileData.attributes.last_analysis_date * 1000).toISOString(),
    permalink: `https://www.virustotal.com/gui/file/${fileData.id}`,
  };
}

async function main() {
  console.log('Uygulama listesi çekiliyor...');
  const appsRes = await fetch(APPS_JSON_URL);
  let apps = await appsRes.json();

  if (TEST_LIMIT) {
    apps = apps.slice(0, TEST_LIMIT);
    console.log(`TEST MODU: sadece ilk ${TEST_LIMIT} uygulama taranacak.`);
  }

  const results = {};
  const existing = fs.existsSync(OUTPUT_FILE)
    ? JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'))
    : {};

  for (const app of apps) {
    if (existing[app.id] && existing[app.id].scanDate) {
      console.log(`[atlanıyor] ${app.name} zaten taranmış (${existing[app.id].scanDate})`);
      results[app.id] = existing[app.id];
      continue;
    }

    try {
      console.log(`[${app.name}] indiriliyor...`);
      const buffer = await downloadFile(app.url);
      const hash = sha256(buffer);
      console.log(`  sha256: ${hash}`);

      let report = await checkExistingReport(hash);
      if (report) {
        console.log('  VT\'de mevcut rapor bulundu, yükleme atlandı.');
        report.permalink = `https://www.virustotal.com/gui/file/${hash}`;
      } else {
        console.log('  VT\'de kayıt yok, yükleniyor ve taranıyor...');
        report = await uploadAndScan(buffer, `${app.name}.apk`);
        report.permalink = `https://www.virustotal.com/gui/file/${hash}`;
      }

      results[app.id] = {
        ...report,
        verdict: report.malicious > 0 ? 'malicious'
          : report.suspicious > 0 ? 'suspicious'
          : 'clean',
      };

      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(results, null, 2));
      console.log(`  ✅ Sonuç: ${results[app.id].verdict} (${report.malicious}/${report.total} motor işaretledi)`);
    } catch (err) {
      console.error(`  ❌ Hata (${app.name}): ${err.message}`);
      results[app.id] = { error: err.message, scanDate: new Date().toISOString() };
      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(results, null, 2));
    }

    console.log(`  ${DELAY_MS / 1000}sn bekleniyor (rate limit)...`);
    await sleep(DELAY_MS);
  }

  console.log(`\nTamamlandı. Sonuçlar ${OUTPUT_FILE} dosyasına yazıldı.`);
  console.log('Bu dosyayı kendi apps.json kaynağına (vtVerdict alanı olarak) birleştirip yayınla.');
}

main().catch((err) => {
  console.error('Beklenmeyen hata:', err);
  process.exit(1);
});
