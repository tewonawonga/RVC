import type { Clip, MediaDetail, MediaSummary, SearchParams } from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${msg}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Media
  listMedia(sort_by = "upload_date", sort_dir = "desc", file_type?: string) {
    const p = new URLSearchParams({ sort_by, sort_dir });
    if (file_type) p.set("file_type", file_type);
    return request<MediaSummary[]>(`/media?${p}`);
  },

  getMedia(id: string) {
    return request<MediaDetail>(`/media/${id}`);
  },

  uploadMedia(formData: FormData) {
    return request<MediaSummary>("/media/upload", { method: "POST", body: formData });
  },

  updateMedia(id: string, data: { origin_date?: string; tags?: string }) {
    const p = new URLSearchParams();
    if (data.origin_date) p.set("origin_date", data.origin_date);
    if (data.tags !== undefined) p.set("tags", data.tags);
    return request<MediaSummary>(`/media/${id}?${p}`, { method: "PATCH" });
  },

  deleteMedia(id: string) {
    return request<void>(`/media/${id}`, { method: "DELETE" });
  },

  mediaFileUrl(item: MediaSummary) {
    return `/uploads/${item.filename}`;
  },

  // Search
  search(params: SearchParams) {
    const p = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && p.set(k, v));
    return request<MediaSummary[]>(`/search?${p}`);
  },

  listTags() {
    return request<string[]>("/search/tags");
  },

  // Clips
  createClip(payload: { media_id: string; title: string; start_time: number; end_time: number }) {
    return request<Clip>("/clips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  listClips(media_id?: string) {
    const p = media_id ? `?media_id=${media_id}` : "";
    return request<Clip[]>(`/clips${p}`);
  },

  clipDownloadUrl(clip: Clip) {
    return `/api/clips/${clip.id}/download`;
  },

  deleteClip(id: string) {
    return request<void>(`/clips/${id}`, { method: "DELETE" });
  },
};
