import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api } from "../api/client";
import type { SearchParams } from "../types";

interface Props {
  params: SearchParams;
  onChange: (p: SearchParams) => void;
}

export default function SearchFilters({ params, onChange }: Props) {
  const { data: allTags = [] } = useQuery({ queryKey: ["tags"], queryFn: api.listTags });

  function set(key: keyof SearchParams, value: string) {
    onChange({ ...params, [key]: value || undefined });
  }

  function clearAll() {
    onChange({ sort_by: params.sort_by, sort_dir: params.sort_dir });
  }

  const hasFilters = !!(params.tags || params.origin_from || params.origin_to || params.upload_from || params.upload_to || params.file_type);

  return (
    <div className="border-t border-gray-800 bg-gray-900/90 px-4 py-3">
      <div className="max-w-screen-xl mx-auto flex flex-wrap gap-3 items-end">
        {/* File type */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Type</label>
          <select
            value={params.file_type || ""}
            onChange={(e) => set("file_type", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All</option>
            <option value="video">Video</option>
            <option value="audio">Audio</option>
          </select>
        </div>

        {/* Origin date range */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Origin from</label>
          <input
            type="date"
            value={params.origin_from || ""}
            onChange={(e) => set("origin_from", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Origin to</label>
          <input
            type="date"
            value={params.origin_to || ""}
            onChange={(e) => set("origin_to", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Upload date range */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Uploaded from</label>
          <input
            type="date"
            value={params.upload_from || ""}
            onChange={(e) => set("upload_from", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Uploaded to</label>
          <input
            type="date"
            value={params.upload_to || ""}
            onChange={(e) => set("upload_to", e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Tags */}
        {allTags.length > 0 && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tags</label>
            <div className="flex flex-wrap gap-1 max-w-xs">
              {allTags.map((tag) => {
                const active = (params.tags || "").split(",").includes(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => {
                      const current = (params.tags || "").split(",").filter(Boolean);
                      const next = active
                        ? current.filter((t) => t !== tag)
                        : [...current, tag];
                      set("tags", next.join(","));
                    }}
                    className={`px-2 py-0.5 rounded text-xs transition-colors ${
                      active
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {hasFilters && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 ml-auto self-end pb-1.5"
          >
            <X className="w-3 h-3" />
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
