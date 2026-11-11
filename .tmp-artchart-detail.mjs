export default async function (page) {
  // Pick a richer Iranian painter if possible
  const candidates = [
    'https://artchart.net/fa/artists/babak-khodabandeh',
    'https://artchart.net/fa/artists/mohammad-masih-eslami',
    'https://artchart.net/fa/artists/hadiseh-soltani',
  ];
  const out = [];
  for (const url of candidates) {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(1500);
    // try click معرفی if present
    try {
      const tab = page.getByText('معرفی', { exact: true }).first();
      if (await tab.count()) await tab.click({ timeout: 2000 });
      await page.waitForTimeout(800);
    } catch (_) {}
    const data = await page.evaluate(() => {
      const get = (sel) => (document.querySelector(sel)?.textContent || '').trim();
      return {
        url: location.href,
        title: document.title,
        h1: get('h1'),
        text: document.body.innerText.slice(0, 4500),
        avatar: document.querySelector('img[src*="avatars/artists"]')?.src || null,
        ogImage: document.querySelector('meta[property="og:image"]')?.content || null,
        description: document.querySelector('meta[name="description"]')?.content || null,
      };
    });
    out.push(data);
  }
  return out;
}
