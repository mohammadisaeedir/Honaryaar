export default async function (page) {
  const el = page.locator('.site-footer');
  await el.scrollIntoViewIfNeeded();
  await el.screenshot({ path: '/Users/khodro45/Desktop/My Code/Ideas/honaryaar/.tmp-figma-assets/footer-128/live-footer.png' });
  return { ok: true };
}
