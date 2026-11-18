export const active = s => Boolean(s && !s.reason);
export function safeName(value) {
  const result = String(value).normalize('NFC').replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_')
    .replace(/[. ]+$/g, '').trim().slice(0, 80).replace(/[. ]+$/g, '');
  if (!result || /^\.+$/.test(result)) throw Error('Enter a title and chapter.');
  return /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(result) ? '_' + result : result;
}
export function settings(input) {
  safeName(input.title); safeName(input.chapter);
  const title = String(input.title).normalize('NFC').trim(), chapter = String(input.chapter).normalize('NFC').trim();
  const max = Number(input.max), timeout = Number(input.timeout);
  if (!Number.isInteger(max) || max < 1 || max > 1000) throw Error('Maximum pages must be 1–1000.');
  if (!Number.isInteger(timeout) || timeout < 5 || timeout > 120) throw Error('Timeout must be 5–120 seconds.');
  const direction=input.direction||'Click';
  if(!['ArrowRight','ArrowLeft','Click'].includes(direction))throw Error('Choose ArrowRight, ArrowLeft or Selected Click Control.');
  return {title, chapter, max, timeout, direction};
}
export function resource(url) {
  const u = new URL(url);
  if (!['http:', 'https:'].includes(u.protocol)) throw Error('Only actual HTTP(S) image resources are supported.');
  u.hash = ''; return u.href;
}
export function extension(url) {
  const ext = new URL(url).pathname.match(/\.(jpe?g|png|webp|gif|avif|bmp)$/i)?.[1];
  return ext?.toLowerCase() || null;
}
export function filename(config, index, ext) {
  if (!/^(jpg|jpeg|png|webp|gif|avif|bmp)$/.test(ext)) throw Error('Image format is unknown. Use a reader exposing a typed image URL.');
  return `Mangas/${safeName(config.title)}/Capítulo ${safeName(config.chapter)}/${String(index).padStart(4, '0')}.${ext}`;
}
export function duplicate(seen, image) {
  return seen.some(p => p.url === image.url || (p.fingerprint && image.fingerprint && p.fingerprint === image.fingerprint));
}
export function stopReason(s, image, now) {
  if (s.count >= s.config.max) return 'safety_limit';
  if (s.phase === 'waiting' && now >= s.deadline) return image ? 'navigation_timeout' : 'image_missing';
  if (image && s.phase !== 'waiting' && duplicate(s.seen, image)) return 'duplicate_page';
  return null;
}
export function inScope(scope, href) {
  const u = new URL(href); return u.origin === scope.origin;
}
export function equivalentScore(d, c) {
  if (!c.width || !c.height) return 0;
  const ratio = Math.min(d.ratio / c.ratio, c.ratio / d.ratio);
  if (ratio < .85) return 0;
  return (d.parent === c.parent ? 4 : 0) + (d.classes && d.classes === c.classes ? 3 : 0)
    + (d.id && d.id === c.id ? 2 : 0) + (d.alt && d.alt === c.alt ? 1 : 0) + ratio;
}
