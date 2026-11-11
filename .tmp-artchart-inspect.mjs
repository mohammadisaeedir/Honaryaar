export default async function (page, ui) {
  const apiHits = [];
  page.on('response', async (res) => {
    const url = res.url();
    if (!/api|graphql|artists|search/i.test(url)) return;
    if (!/\.json|\/api\/|graphql/i.test(url) && !url.includes('artists')) return;
    try {
      const ct = res.headers()['content-type'] || '';
      if (!ct.includes('json') && !ct.includes('javascript')) return;
      const text = await res.text();
      apiHits.push({ url, status: res.status(), sample: text.slice(0, 4000) });
    } catch (_) {}
  });

  await page.goto('https://artchart.net/fa/artists/alan-sakhavarz', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2500);
  const detail = await page.evaluate(() => {
    const text = document.body.innerText;
    const imgs = [...document.querySelectorAll('img')].slice(0, 12).map(img => ({src: img.src, alt: img.alt}));
    const meta = {};
    document.querySelectorAll('meta').forEach(m => {
      const k = m.getAttribute('property') || m.getAttribute('name');
      if (k) meta[k] = m.getAttribute('content');
    });
    return {
      url: location.href,
      title: document.title,
      text: text.slice(0, 3500),
      imgs,
      meta,
      nextData: window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__).slice(0, 8000) : null,
      nuxt: window.__NUXT__ ? JSON.stringify(window.__NUXT__).slice(0, 8000) : null,
    };
  });

  await page.goto('https://artchart.net/fa/artists/search?art_categories[0]=painting', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  const listing = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('a[href*="/fa/artists/"]')]
      .filter(a => /\/fa\/artists\/[^/]+$/.test(a.pathname) && a.pathname !== '/fa/artists')
      .slice(0, 8)
      .map(a => ({
        href: a.href,
        slug: a.pathname.split('/').pop(),
        text: a.innerText.trim().replace(/\s+/g, ' ').slice(0, 120),
        img: (a.querySelector('img') || {}).src || null,
      }));
    return {
      resultHint: (document.body.innerText.match(/(\d+)\s*نتیجه/) || [])[1] || null,
      cards,
      nextData: window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__).slice(0, 12000) : null,
    };
  });

  return { detail, listing, apiHits: apiHits.slice(0, 15) };
}
