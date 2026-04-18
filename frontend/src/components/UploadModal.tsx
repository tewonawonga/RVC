import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { X, Upload, File as FileIcon, Loader } from "lucide-react";
import { api } from "../api/client";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function UploadModal({ onClose, onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [originDate, setOriginDate] = useState("");
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "audio/*": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"],
      "video/*": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"],
    },
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (originDate) fd.append("origin_date", originDate);
      if (tags) fd.append("tags", tags);
      await api.uploadMedia(fd);
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">Upload Media</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Drop zone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              isDragActive
                ? "border-blue-500 bg-blue-950/30"
                : file
                ? "border-green-600 bg-green-950/20"
                : "border-gray-700 hover:border-gray-500"
            }`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex items-center justify-center gap-2 text-green-400">
                <FileIcon className="w-5 h-5" />
                <span className="text-sm truncate max-w-[200px]">{file.name}</span>
              </div>
            ) : (
              <div>
                <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                <p className="text-sm text-gray-400">
                  {isDragActive ? "Drop it here" : "Drag & drop or click to select"}
                </p>
                <p className="text-xs text-gray-600 mt-1">MP4, MOV, MP3, WAV, FLAC, and more</p>
              </div>
            )}
          </div>

          {/* Origin date */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">
              Origin date <span className="text-gray-600">(optional)</span>
            </label>
            <input
              type="date"
              value={originDate}
              onChange={(e) => setOriginDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">
              Tags <span className="text-gray-600">(comma-separated, optional)</span>
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. hearing, senate, 2024"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg border border-gray-700 text-sm text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || loading}
              className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {loading ? "Uploading…" : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
