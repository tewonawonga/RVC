import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader, AlertCircle } from "lucide-react";
import { api } from "../api/client";
import MediaPlayer from "./MediaPlayer";
import TranscriptPanel from "./TranscriptPanel";

export default function MediaPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: item, isLoading, error } = useQuery({
    queryKey: ["media", id],
    queryFn: () => api.getMedia(id!),
    refetchInterval: (query) => {
      const status = query.state.data?.transcription_status;
      return status === "pending" || status === "processing" ? 3000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader className="w-8 h-8 text-gray-500 animate-spin" />
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center flex-col gap-3">
        <AlertCircle className="w-8 h-8 text-red-400" />
        <p className="text-gray-400">Media not found.</p>
        <Link to="/" className="text-blue-400 text-sm hover:underline">← Back to library</Link>
      </div>
    );
  }

  const fileUrl = api.mediaFileUrl(item);

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 px-4 py-3 flex items-center gap-3">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Library
        </Link>
        <span className="text-gray-600">/</span>
        <span className="text-sm text-gray-200 truncate max-w-md">{item.original_filename}</span>
      </header>

      {/* Body: player left, transcript right */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden">
        <MediaPlayer item={item} fileUrl={fileUrl} />
        <TranscriptPanel item={item} onClipCreated={() => qc.invalidateQueries({ queryKey: ["clips", id] })} />
      </div>
    </div>
  );
}
