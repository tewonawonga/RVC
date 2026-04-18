import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Scissors, Download, Trash2, Loader, CheckCircle, AlertCircle, Clock
} from "lucide-react";
import { format } from "date-fns";
import type { MediaDetail, TranscriptSegment, Clip } from "../types";
import { api } from "../api/client";
import { playerRefs, seekCallbacks } from "./MediaPlayer";

function formatTime(secs: number) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface Props {
  item: MediaDetail;
  onClipCreated: () => void;
}

export default function TranscriptPanel({ item, onClipCreated }: Props) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"transcript" | "clips">("transcript");
  const [currentTime, setCurrentTime] = useState(0);
  const [clipStart, setClipStart] = useState<number | null>(null);
  const [clipEnd, setClipEnd] = useState<number | null>(null);
  const [clipTitle, setClipTitle] = useState("");
  const [showClipForm, setShowClipForm] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const activeSegRef = useRef<HTMLButtonElement>(null);

  // Poll media player's currentTime via rAF
  useEffect(() => {
    let raf: number;
    function tick() {
      const el = playerRefs[item.id]?.current;
      if (el) setCurrentTime(el.currentTime);
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [item.id]);

  // Auto-scroll transcript to active segment
  useEffect(() => {
    activeSegRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [currentTime]);

  const activeSegIndex = item.transcript_segments.findIndex(
    (s) => currentTime >= s.start_time && currentTime < s.end_time
  );

  function clickSegment(seg: TranscriptSegment) {
    seekCallbacks[item.id]?.(seg.start_time);
  }

  function markStart(seg: TranscriptSegment) {
    setClipStart(seg.start_time);
    if (clipEnd !== null && seg.start_time >= clipEnd) setClipEnd(null);
    setShowClipForm(true);
  }

  function markEnd(seg: TranscriptSegment) {
    setClipEnd(seg.end_time);
    setShowClipForm(true);
  }

  const { data: clips = [], isLoading: clipsLoading } = useQuery({
    queryKey: ["clips", item.id],
    queryFn: () => api.listClips(item.id),
    refetchInterval: (q) =>
      q.state.data?.some((c) => !c.file_path) ? 3000 : false,
  });

  const createClipMutation = useMutation({
    mutationFn: api.createClip,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clips", item.id] });
      onClipCreated();
      setClipStart(null);
      setClipEnd(null);
      setClipTitle("");
      setShowClipForm(false);
      setActiveTab("clips");
    },
  });

  const deleteClipMutation = useMutation({
    mutationFn: api.deleteClip,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clips", item.id] }),
  });

  function submitClip() {
    if (clipStart === null || clipEnd === null || !clipTitle.trim()) return;
    createClipMutation.mutate({
      media_id: item.id,
      title: clipTitle.trim(),
      start_time: clipStart,
      end_time: clipEnd,
    });
  }

  const hasTranscript = item.transcription_status === "complete" && item.transcript_segments.length > 0;

  return (
    <div className="flex flex-col lg:w-5/12 xl:w-4/12 bg-gray-900 min-h-0">
      {/* Tabs */}
      <div className="flex border-b border-gray-800 flex-shrink-0">
        {(["transcript", "clips"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-sm font-medium transition-colors capitalize ${
              activeTab === tab
                ? "text-white border-b-2 border-blue-500"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab}
            {tab === "clips" && clips.length > 0 && (
              <span className="ml-1.5 text-xs bg-gray-700 text-gray-300 rounded-full px-1.5 py-0.5">
                {clips.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Clip extraction form */}
      {showClipForm && activeTab === "transcript" && (
        <div className="border-b border-gray-800 px-4 py-3 bg-gray-950 flex-shrink-0">
          <p className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
            <Scissors className="w-3.5 h-3.5 text-blue-400" /> Extract Clip
          </p>
          <div className="grid grid-cols-2 gap-2 mb-2 text-xs">
            <div className="bg-gray-800 rounded px-2 py-1.5">
              <span className="text-gray-500">Start: </span>
              <span className={clipStart !== null ? "text-green-400" : "text-gray-600"}>
                {clipStart !== null ? formatTime(clipStart) : "not set"}
              </span>
            </div>
            <div className="bg-gray-800 rounded px-2 py-1.5">
              <span className="text-gray-500">End: </span>
              <span className={clipEnd !== null ? "text-green-400" : "text-gray-600"}>
                {clipEnd !== null ? formatTime(clipEnd) : "not set"}
              </span>
            </div>
          </div>
          <input
            value={clipTitle}
            onChange={(e) => setClipTitle(e.target.value)}
            placeholder="Clip title…"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-blue-500 mb-2"
          />
          <div className="flex gap-2">
            <button
              onClick={() => { setShowClipForm(false); setClipStart(null); setClipEnd(null); }}
              className="flex-1 py-1.5 text-xs rounded border border-gray-700 text-gray-400 hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={submitClip}
              disabled={clipStart === null || clipEnd === null || !clipTitle.trim() || createClipMutation.isPending}
              className="flex-1 py-1.5 text-xs rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white flex items-center justify-center gap-1"
            >
              {createClipMutation.isPending ? <Loader className="w-3 h-3 animate-spin" /> : <Scissors className="w-3 h-3" />}
              Extract
            </button>
          </div>
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto" ref={transcriptRef}>
        {activeTab === "transcript" && (
          <div className="p-2">
            {item.transcription_status === "pending" && (
              <StatusMessage icon={<Clock className="w-5 h-5 text-gray-500" />} text="Transcription queued…" />
            )}
            {item.transcription_status === "processing" && (
              <StatusMessage icon={<Loader className="w-5 h-5 text-yellow-400 animate-spin" />} text="Transcribing…" />
            )}
            {item.transcription_status === "failed" && (
              <StatusMessage icon={<AlertCircle className="w-5 h-5 text-red-400" />} text="Transcription failed." />
            )}
            {item.transcription_status === "complete" && item.transcript_segments.length === 0 && (
              <StatusMessage icon={<CheckCircle className="w-5 h-5 text-gray-500" />} text="No speech detected." />
            )}

            {hasTranscript && item.transcript_segments.map((seg, idx) => {
              const isActive = idx === activeSegIndex;
              const isClipStart = clipStart === seg.start_time;
              const isClipEnd = clipEnd === seg.end_time;
              const inRange = clipStart !== null && clipEnd !== null &&
                seg.start_time >= clipStart && seg.end_time <= clipEnd;

              return (
                <div
                  key={seg.id}
                  className={`group flex gap-2 rounded-lg px-2 py-1.5 mb-0.5 transition-colors ${
                    isActive ? "bg-blue-950/60 border border-blue-800/50" : inRange ? "bg-blue-950/30" : "hover:bg-gray-800/50"
                  }`}
                >
                  <button
                    ref={isActive ? (activeSegRef as any) : undefined}
                    onClick={() => clickSegment(seg)}
                    className="text-xs text-gray-500 hover:text-blue-400 tabular-nums min-w-[38px] pt-0.5 text-left transition-colors"
                  >
                    {formatTime(seg.start_time)}
                  </button>
                  <p
                    className={`text-sm flex-1 leading-relaxed cursor-pointer ${
                      isActive ? "text-white" : "text-gray-300"
                    }`}
                    onClick={() => clickSegment(seg)}
                  >
                    {seg.text}
                  </p>
                  {/* Clip mark buttons */}
                  <div className="opacity-0 group-hover:opacity-100 flex items-start gap-1 transition-opacity flex-shrink-0">
                    <button
                      onClick={() => markStart(seg)}
                      title="Set clip start"
                      className={`text-xs px-1.5 py-0.5 rounded transition-colors ${isClipStart ? "bg-green-700 text-white" : "bg-gray-800 text-gray-500 hover:text-green-400"}`}
                    >
                      [
                    </button>
                    <button
                      onClick={() => markEnd(seg)}
                      title="Set clip end"
                      className={`text-xs px-1.5 py-0.5 rounded transition-colors ${isClipEnd ? "bg-green-700 text-white" : "bg-gray-800 text-gray-500 hover:text-green-400"}`}
                    >
                      ]
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "clips" && (
          <div className="p-3 space-y-3">
            {clipsLoading && <StatusMessage icon={<Loader className="w-5 h-5 animate-spin text-gray-500" />} text="Loading clips…" />}
            {!clipsLoading && clips.length === 0 && (
              <StatusMessage
                icon={<Scissors className="w-5 h-5 text-gray-600" />}
                text="No clips yet. Use the [ ] buttons in the transcript to mark a range."
              />
            )}
            {clips.map((clip) => (
              <ClipRow key={clip.id} clip={clip} onDelete={() => deleteClipMutation.mutate(clip.id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusMessage({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-500">
      {icon}
      <p className="text-sm text-center max-w-[200px]">{text}</p>
    </div>
  );
}

function ClipRow({ clip, onDelete }: { clip: Clip; onDelete: () => void }) {
  const ready = !!clip.file_path;
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-100 truncate">{clip.title}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
            <span className="ml-2 text-gray-600">
              ({Math.ceil(clip.end_time - clip.start_time)}s)
            </span>
          </p>
          <p className="text-xs text-gray-600 mt-0.5">{format(new Date(clip.created_at), "MMM d, h:mm a")}</p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {ready ? (
            <a
              href={api.clipDownloadUrl(clip)}
              download
              className="p-1.5 rounded bg-blue-700 hover:bg-blue-600 text-white transition-colors"
              title="Download"
            >
              <Download className="w-3.5 h-3.5" />
            </a>
          ) : (
            <span className="p-1.5 text-yellow-500" title="Processing…">
              <Loader className="w-3.5 h-3.5 animate-spin" />
            </span>
          )}
          <button
            onClick={() => { if (confirm("Delete this clip?")) onDelete(); }}
            className="p-1.5 rounded bg-gray-700 hover:bg-red-900/60 text-gray-400 hover:text-red-400 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

