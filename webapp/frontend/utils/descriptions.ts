// Shared by the descriptions page and its modals. labelsKey is the key of the entity list in the
// /api/all_labels response.
export const descriptionEntityTypes = [
  { value: "person", label: "Személy", labelsKey: "person", badgeClass: "bg-red-100 text-red-700" },
  { value: "institution", label: "Intézmény", labelsKey: "institution", badgeClass: "bg-blue-100 text-blue-700" },
  { value: "file", label: "Akta", labelsKey: "files", badgeClass: "bg-orange-100 text-orange-700" },
  { value: "newspaper", label: "Újság", labelsKey: "domains", badgeClass: "bg-green-100 text-green-700" },
];

export const descriptionStatuses: Record<string, { label: string; badgeClass: string }> = {
  queued: { label: "Feldolgozás alatt", badgeClass: "bg-gray-100 text-gray-700" },
  review: { label: "Ellenőrizendő", badgeClass: "bg-amber-100 text-amber-800" },
  accepted: { label: "Elfogadva", badgeClass: "bg-green-100 text-green-700" },
  rejected: { label: "Elutasítva", badgeClass: "bg-gray-200 text-gray-600" },
  error: { label: "Hiba", badgeClass: "bg-red-100 text-red-700" },
};

export function descriptionEntityType(value: string) {
  return descriptionEntityTypes.find((t) => t.value === value);
}

// The sources are the links of the description HTML.
export function linkedUrls(html: string): string[] {
  const links = new DOMParser().parseFromString(html, "text/html").querySelectorAll("a[href]");
  const urls = [...links].map((a) => a.getAttribute("href")!).filter((href) => /^https?:\/\//.test(href));
  return [...new Set(urls)];
}

export function normalizeUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

// The backend sends the naive DATETIMEs of the db as if they were GMT, so they are shown in UTC to
// get back the original wall-clock time.
export function formatDescriptionDate(value: string | null): string {
  if (!value) return "";
  return new Date(value).toLocaleString("hu-HU", {
    timeZone: "UTC",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
