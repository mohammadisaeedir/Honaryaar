export default async function (page, ui) {
  const el = page.locator('.footer-promo');
  await el.scrollIntoViewIfNeeded();
  await el.screenshot({ path: '/Users/khodro45/Desktop/My Code/Ideas/honaryaar/.tmp-figma-assets/post-call-promo.png' });
  return { ok: true };
}
