import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, Search, SlidersHorizontal } from "lucide-react";
import { api } from "../api/client";
import type { SearchParams } from "../types";
import MediaCard from "./MediaCard";
import UploadModal from "./UploadModal";
import SearchFilters from "./SearchFilters";

export default function LibraryPage() {
  const qc = useQueryClient();
  const [showUpload, setShowUpload] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [params, setParams] = useState<SearchParams>({
    sort_by: "upload_date",
    sort_dir: "desc",
  });
  const [searchInput, setSearchInput] = useState("");

  const isSearching = Object.values(params).some(Boolean) || searchInput;
  const queryParams: SearchParams = { ...params, q: searchInput || undefined };

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["media", queryParams],
    queryFn: () =>
      searchInput || Object.keys(params).length
        ? api.search(queryParams)
        : api.listMedia(params.sort_by, params.sort_dir, params.file_type),
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteMedia,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["media"] }),
  });

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-30">
        <div className="max-w-screen-xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="flex items-center gap-2 mr-4">
            <span className="text-2xl">🎬</span>
            <span className="font-semibold text-white text-lg tracking-tight">Media Library</span>
          </div>

          {/* Search bar */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search filenames, transcripts, tags…"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors ${
              showFilters || Object.values(params).some(Boolean)
                ? "bg-blue-600 border-blue-500 text-white"
                : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </button>

          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm text-white font-medium transition-colors"
          >
            <Upload className="w-4 h-4" />
            Upload
          </button>
        </div>

        {showFilters && (
          <SearchFilters params={params} onChange={setParams} />
        )}
      </header>

      {/* Content */}
      <main className="max-w-screen-xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-400">
            {isLoading ? "Loading…" : `${items.length} item${items.length !== 1 ? "s" : ""}`}
          </p>
          <select
            value={`${params.sort_by}:${params.sort_dir}`}
            onChange={(e) => {
              const [sort_by, sort_dir] = e.target.value.split(":");
              setParams((p) => ({ ...p, sort_by, sort_dir }));
            }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="upload_date:desc">Newest upload</option>
            <option value="upload_date:asc">Oldest upload</option>
            <option value="origin_date:desc">Newest origin</option>
            <option value="origin_date:asc">Oldest origin</option>
            <option value="filename:asc">Filename A–Z</option>
            <option value="filename:desc">Filename Z–A</option>
            <option value="duration:desc">Longest first</option>
            <option value="duration:asc">Shortest first</option>
          </select>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-gray-900 rounded-xl h-52 animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-4xl mb-3">📂</p>
            <p className="text-gray-400 text-lg">No media found</p>
            <p className="text-gray-600 text-sm mt-1">Upload a file to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {items.map((item) => (
              <MediaCard
                key={item.id}
                item={item}
                onDelete={() => deleteMutation.mutate(item.id)}
              />
            ))}
          </div>
        )}
      </main>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ["media"] });
            setShowUpload(false);
          }}
        />
      )}
    </div>
  );
}
