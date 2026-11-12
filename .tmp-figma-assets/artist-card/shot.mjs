export default async function (page) {
  const tile = page.locator('.artist-tile').first();
  await tile.scrollIntoViewIfNeeded();
  await tile.screenshot({ path: '/Users/khodro45/Desktop/My Code/Ideas/honaryaar/.tmp-figma-assets/artist-card/live-tile.png' });
  return { ok: true };
}
