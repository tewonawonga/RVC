import { Link } from "react-router-dom";
import { Trash2, Clock, Film, Music, Tag as TagIcon, CheckCircle, Loader, AlertCircle, Circle } from "lucide-react";
import { format } from "date-fns";
import type { MediaSummary } from "../types";

function formatDuration(secs: number | null) {
  if (!secs) return null;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatBytes(n: number | null) {
  if (!n) return null;
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

const statusIcon = {
  pending: <Circle className="w-3.5 h-3.5 text-gray-500" />,
  processing: <Loader className="w-3.5 h-3.5 text-yellow-400 animate-spin" />,
  complete: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
  failed: <AlertCircle className="w-3.5 h-3.5 text-red-400" />,
};
const statusLabel = {
  pending: "Queued",
  processing: "Transcribing…",
  complete: "Transcribed",
  failed: "Failed",
};

interface Props {
  item: MediaSummary;
  onDelete: () => void;
}

export default function MediaCard({ item, onDelete }: Props) {
  const Icon = item.file_type === "video" ? Film : Music;

  return (
    <div className="group relative bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-colors">
      {/* Thumbnail area */}
      <Link to={`/media/${item.id}`} className="block">
        <div className="bg-gray-800 h-32 flex items-center justify-center">
          <Icon className="w-12 h-12 text-gray-600" />
        </div>
      </Link>

      {/* Delete button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          if (confirm(`Delete "${item.original_filename}"?`)) onDelete();
        }}
        className="absolute top-2 right-2 p-1.5 bg-gray-900/80 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-900/80 hover:text-red-400 text-gray-500"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>

      {/* Info */}
      <Link to={`/media/${item.id}`} className="block p-3">
        <p className="text-sm font-medium text-gray-100 truncate" title={item.original_filename}>
          {item.original_filename}
        </p>

        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
          {item.duration && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDuration(item.duration)}
            </span>
          )}
          {item.file_size && <span>{formatBytes(item.file_size)}</span>}
          {item.origin_date && (
            <span>{format(new Date(item.origin_date), "MMM d, yyyy")}</span>
          )}
        </div>

        {/* Tags */}
        {item.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {item.tags.map((t) => (
              <span
                key={t.id}
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-800 rounded text-xs text-gray-400"
              >
                <TagIcon className="w-2.5 h-2.5" />
                {t.name}
              </span>
            ))}
          </div>
        )}

        {/* Transcription status */}
        <div className="mt-2 flex items-center gap-1.5 text-xs text-gray-500">
          {statusIcon[item.transcription_status]}
          {statusLabel[item.transcription_status]}
        </div>
      </Link>
    </div>
  );
}
