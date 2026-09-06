export interface EmbedInfo {
  originalUrl: string;
  formattedUrl: string;
  embedUrl: string;
  platform: "youtube" | "spotify" | "figma" | "vimeo" | "netflix" | "general";
  platformName: string;
  title: string;
  faviconUrl: string;
  canDirectIframe: boolean;
  isStreamingProtected: boolean;
  mediaId?: string;
}

export function resolveEmbed(rawUrl?: string, useProxy: boolean = true): EmbedInfo {
  if (!rawUrl || !rawUrl.trim()) {
    return {
      originalUrl: "",
      formattedUrl: "",
      embedUrl: "",
      platform: "general",
      platformName: "Website",
      title: "No URL provided",
      faviconUrl: "",
      canDirectIframe: false,
      isStreamingProtected: false,
    };
  }

  let url = rawUrl.trim();
  if (!url.startsWith("http://") && !url.startsWith("https://") && !url.startsWith("/")) {
    url = "https://" + url;
  }
  const sameOrigin =
    url.startsWith("/") ||
    (typeof window !== "undefined" && url.startsWith(window.location.origin));

  let hostname = "";
  try {
    hostname = new URL(url).hostname;
  } catch {
    hostname = "website.com";
  }

  const faviconUrl = `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`;

  // 1. YouTube
  const ytMatch = url.match(
    /(?:youtube\.com\/(?:watch\?v=|shorts\/|live\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
  );
  if (ytMatch && ytMatch[1]) {
    const videoId = ytMatch[1];
    return {
      originalUrl: rawUrl,
      formattedUrl: url,
      embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=0&rel=0`,
      platform: "youtube",
      platformName: "YouTube",
      title: `YouTube Video (${videoId})`,
      faviconUrl: "https://www.youtube.com/s/desktop/f1721ae6/img/favicon_144x144.png",
      canDirectIframe: true,
      isStreamingProtected: false,
      mediaId: videoId,
    };
  }

  // 2. Spotify
  const spotifyMatch = url.match(
    /open\.spotify\.com\/(track|album|playlist|artist|episode)\/([a-zA-Z0-9]+)/,
  );
  if (spotifyMatch) {
    const [, type, id] = spotifyMatch;
    return {
      originalUrl: rawUrl,
      formattedUrl: url,
      embedUrl: `https://open.spotify.com/embed/${type}/${id}`,
      platform: "spotify",
      platformName: "Spotify",
      title: `Spotify ${type.charAt(0).toUpperCase() + type.slice(1)}`,
      faviconUrl: "https://open.spotifycdn.com/cdn/images/favicon32.b64ecc03.png",
      canDirectIframe: true,
      isStreamingProtected: false,
      mediaId: id,
    };
  }

  // 3. Figma
  if (
    url.includes("figma.com/file/") ||
    url.includes("figma.com/proto/") ||
    url.includes("figma.com/design/")
  ) {
    return {
      originalUrl: rawUrl,
      formattedUrl: url,
      embedUrl: `https://www.figma.com/embed?embed_host=coherence&url=${encodeURIComponent(url)}`,
      platform: "figma",
      platformName: "Figma",
      title: "Figma Design File",
      faviconUrl: "https://static.figma.com/app/icon/1/favicon.png",
      canDirectIframe: true,
      isStreamingProtected: false,
    };
  }

  // 4. Vimeo
  const vimeoMatch = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  if (vimeoMatch && vimeoMatch[1]) {
    const videoId = vimeoMatch[1];
    return {
      originalUrl: rawUrl,
      formattedUrl: url,
      embedUrl: `https://player.vimeo.com/video/${videoId}`,
      platform: "vimeo",
      platformName: "Vimeo",
      title: `Vimeo Video (${videoId})`,
      faviconUrl: "https://f.vimeocdn.com/images_v6/favicon.ico",
      canDirectIframe: true,
      isStreamingProtected: false,
      mediaId: videoId,
    };
  }

  // 5. Netflix
  if (url.includes("netflix.com")) {
    const jbvMatch = url.match(/[?&]jbv=(\d+)/) || url.match(/title\/(\d+)/);
    const mediaId = jbvMatch ? jbvMatch[1] : undefined;
    const title = mediaId ? `Netflix Title #${mediaId}` : "Netflix Streaming Video";
    return {
      originalUrl: rawUrl,
      formattedUrl: url,
      embedUrl: useProxy ? `/api/proxy-site?url=${encodeURIComponent(url)}` : url,
      platform: "netflix",
      platformName: "Netflix",
      title,
      faviconUrl: "https://assets.nflxext.com/us/ffe/siteui/common/icons/nficon2016.ico",
      canDirectIframe: false,
      isStreamingProtected: true,
      mediaId,
    };
  }

  // 6. General websites. Same-origin pages (the demo fixture) are the
  // product under test — do not send them through /api/proxy-site, which
  // is a Vite preview helper, not Lithium/Boron.
  return {
    originalUrl: rawUrl,
    formattedUrl: url,
    embedUrl: sameOrigin || !useProxy ? url : `/api/proxy-site?url=${encodeURIComponent(url)}`,
    platform: "general",
    platformName: hostname || url,
    title: hostname || url,
    faviconUrl,
    canDirectIframe: sameOrigin,
    isStreamingProtected: false,
  };
}
