const TWITTER_EMBED_RE = /https?:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)(?:\/photo\/(\d+))?[^\s<>"']*/g;

export function replaceTwitterUrls(text: string): string {
  return text.replace(TWITTER_EMBED_RE, (match, user: string, tweetId: string, photo: string | undefined) => {
    let attrs = `data-user="${user}" data-tweet-id="${tweetId}"`;
    if (photo) attrs += ` data-photo="${photo}"`;
    return `<div class="twitter-embed" ${attrs}><div class="twitter-embed-loading">Loading…</div></div>`;
  });
}

function fmtNum(n: string): string {
  const num = parseInt(n, 10);
  if (isNaN(num)) return n;
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(num % 1_000_000 === 0 ? 0 : 1).replace(/\.0$/, "") + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(num % 1_000 === 0 ? 0 : 1).replace(/\.0$/, "") + "k";
  return num.toLocaleString();
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const tweetCache = new Map<string, any>();

export async function hydrateTwitterEmbeds(): Promise<void> {
  const embeds = document.querySelectorAll<HTMLElement>(".twitter-embed");
  const pending: { el: HTMLElement; user: string; tweetId: string; photo?: string }[] = [];
  for (const el of embeds) {
    const user = el.dataset.user;
    const tweetId = el.dataset.tweetId;
    if (!user || !tweetId) continue;
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
      const name = author.name || user;
      const tweetUrl = `https://x.com/${user}/status/${tweetId}`;
      const photos = t.media?.photos || [];
      const videos = t.media?.video || null;
      const text = t.text || "";
      const likes = t.likes !== undefined ? String(t.likes) : "";
      const retweets = t.retweets !== undefined ? String(t.retweets) : "";
      const replies = t.replies !== undefined ? String(t.replies) : "";
      const views = t.views !== undefined ? String(t.views) : "";
      let mediaHtml = "";
      if (photo) {
        const img = photos[parseInt(photo) - 1];
        if (img) mediaHtml = `<img class="twitter-embed-image" src="${img.url}" alt="" loading="lazy" />`;
      } else if (videos) {
        mediaHtml = `<video class="twitter-embed-video" src="${videos.url}" controls playsinline preload="metadata"></video>`;
      } else if (photos.length === 1) {
        mediaHtml = `<img class="twitter-embed-image" src="${photos[0].url}" alt="" loading="lazy" />`;
      } else if (photos.length > 1) {
        mediaHtml = `<div class="twitter-embed-grid">${photos.map((p: any) =>
          `<img class="twitter-embed-image" src="${p.url}" alt="" loading="lazy" />`
        ).join("")}</div>`;
      }
      el.innerHTML = `
        <div class="twitter-embed-inner">
          <div class="twitter-embed-header">
            <a class="twitter-embed-name" href="${tweetUrl}" target="_blank" rel="noopener noreferrer">${escHtml(name)}</a>
            <span class="twitter-embed-user">@${user}</span>
            <svg class="twitter-embed-x-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
          </div>
          ${text ? `<p class="twitter-embed-text">${escHtml(text)}</p>` : ""}
          ${mediaHtml}
          <div class="twitter-embed-stats">
            <span class="twitter-embed-stat" title="Views">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              ${fmtNum(views)}
            </span>
            <span class="twitter-embed-stat" title="Replies">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              ${fmtNum(replies)}
            </span>
            <span class="twitter-embed-stat" title="Reposts">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
              ${fmtNum(retweets)}
            </span>
            <span class="twitter-embed-stat" title="Likes">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              ${fmtNum(likes)}
            </span>
          </div>
        </div>
      `;
    } catch {
      el.innerHTML = '<div class="twitter-embed-error">Failed to load tweet</div>';
    }
  }));
}
