const TWITTER_EMBED_RE = /https?:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)(?:\/photo\/(\d+))?[^\s<>"']*/g;

export function replaceTwitterUrls(text: string): string {
  return text.replace(TWITTER_EMBED_RE, (match, user: string, tweetId: string, photo: string | undefined) => {
    let attrs = `data-user="${user}" data-tweet-id="${tweetId}"`;
    if (photo) attrs += ` data-photo="${photo}"`;
    return `<div class="twitter-embed" ${attrs}><div class="twitter-embed-loading">Loading…</div></div>`;
  });
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const tweetCache = new Map<string, any>();
const disabledArtists = new Set<string>();

export function setDisabledArtists(users: string[]): void {
  disabledArtists.clear();
  for (const user of users) disabledArtists.add(user.toLowerCase());
  if (typeof document === "undefined") return;
  for (const el of document.querySelectorAll<HTMLElement>(".twitter-embed")) {
    const user = el.dataset.user;
    if (user) el.hidden = disabledArtists.has(user.toLowerCase());
  }
}

export async function hydrateTwitterEmbeds(): Promise<void> {
  const embeds = document.querySelectorAll<HTMLElement>(".twitter-embed");
  const pending: { el: HTMLElement; user: string; tweetId: string; photo?: string }[] = [];
  for (const el of embeds) {
    const user = el.dataset.user;
    const tweetId = el.dataset.tweetId;
    if (!user || !tweetId) continue;
    if (disabledArtists.has(user.toLowerCase())) el.hidden = true;
    if (el.querySelector(".twitter-embed-inner")) continue;
    pending.push({ el, user, tweetId, photo: el.dataset.photo });
  }
  if (!pending.length) return;
  await Promise.allSettled(pending.map(async ({ el, user, tweetId, photo }) => {
    try {
      const cacheKey = `${user}/${tweetId}`;
      if (!tweetCache.has(cacheKey)) {
        const res = await fetch(`https://api.fxtwitter.com/${user}/status/${tweetId}`);
        const data = await res.json();
        if (!data?.tweet) throw new Error("no tweet data");
        tweetCache.set(cacheKey, data.tweet);
      }
      const t = tweetCache.get(cacheKey);
      const author = t.author || {};
      const avatar = author.avatar_url || author.profile_image_url || "";
      const profileUrl = `https://x.com/${user}`;
      const tweetUrl = `https://x.com/${user}/status/${tweetId}`;
      const photos = t.media?.photos || [];
      const videos = t.media?.video || null;
      const photoIndex = photo ? parseInt(photo, 10) - 1 : (!videos && photos.length === 1 ? 0 : -1);
      const singlePhoto = photoIndex >= 0 ? photos[photoIndex] : null;
      const hasSinglePhoto = Boolean(singlePhoto?.width && singlePhoto?.height);
      el.classList.toggle("twitter-embed--single", hasSinglePhoto);
      if (hasSinglePhoto) {
        el.style.setProperty("--embed-aspect", String(singlePhoto.width / singlePhoto.height));
      } else {
        el.style.removeProperty("--embed-aspect");
      }
      // Twitter's image CDN rejects hotlinked requests that include our referrer.
      let mediaHtml = "";
      if (photo) {
        const img = photos[parseInt(photo) - 1];
        if (img) mediaHtml = `<img class="twitter-embed-image" src="${img.url}" alt="" loading="lazy" referrerpolicy="no-referrer" />`;
      } else if (videos) {
        mediaHtml = `<video class="twitter-embed-video" src="${videos.url}" controls playsinline preload="metadata"></video>`;
      } else if (photos.length === 1) {
        mediaHtml = `<img class="twitter-embed-image" src="${photos[0].url}" alt="" loading="lazy" referrerpolicy="no-referrer" />`;
      } else if (photos.length > 1) {
        mediaHtml = `<div class="twitter-embed-grid">${photos.map((p: any) =>
          `<img class="twitter-embed-image" src="${p.url}" alt="" loading="lazy" referrerpolicy="no-referrer" />`
        ).join("")}</div>`;
      }
      el.innerHTML = `
        <figure class="twitter-embed-inner">
          <div class="twitter-embed-header">
            <a class="twitter-embed-author" href="${profileUrl}" target="_blank" rel="noopener noreferrer">
              ${avatar ? `<img class="twitter-embed-avatar" src="${escHtml(avatar)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : ""}
              <span class="twitter-embed-user">@${escHtml(user)}</span>
            </a>
            <a class="twitter-embed-x-icon" href="${tweetUrl}" target="_blank" rel="noopener noreferrer" aria-label="View on X">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
          </div>
          ${mediaHtml}
          <figcaption class="twitter-embed-caption"><a href="${tweetUrl}" target="_blank" rel="noopener noreferrer">Illustration by @${escHtml(user)} on X</a></figcaption>
        </figure>
      `;
    } catch {
      el.innerHTML = '<div class="twitter-embed-error">Failed to load tweet</div>';
    }
  }));
}
