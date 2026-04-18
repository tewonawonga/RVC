import { useRef, useState, useEffect, useCallback } from "react";
import {
  Play, Pause, Volume2, VolumeX, Maximize2, SkipBack, SkipForward, Tag as TagIcon
} from "lucide-react";
import { format } from "date-fns";
import type { MediaDetail } from "../types";

function formatTime(secs: number) {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface Props {
  item: MediaDetail;
  fileUrl: string;
}

// Expose playback time to siblings via a simple global ref map
export const playerRefs: Record<string, React.MutableRefObject<HTMLVideoElement | HTMLAudioElement | null>> = {};
export const seekCallbacks: Record<string, (t: number) => void> = {};

export default function MediaPlayer({ item, fileUrl }: Props) {
  const mediaRef = useRef<HTMLVideoElement & HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    playerRefs[item.id] = mediaRef as any;
    seekCallbacks[item.id] = (t: number) => {
      if (mediaRef.current) {
        mediaRef.current.currentTime = t;
        mediaRef.current.play();
        setPlaying(true);
      }
    };
    return () => {
      delete playerRefs[item.id];
      delete seekCallbacks[item.id];
    };
  }, [item.id]);

  const onTimeUpdate = useCallback(() => {
    setCurrentTime(mediaRef.current?.currentTime ?? 0);
  }, []);

  const onLoadedMetadata = useCallback(() => {
    setDuration(mediaRef.current?.duration ?? 0);
  }, []);

  function togglePlay() {
    if (!mediaRef.current) return;
    if (playing) {
      mediaRef.current.pause();
    } else {
      mediaRef.current.play();
    }
    setPlaying(!playing);
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    if (!progressRef.current || !duration) return;
    const rect = progressRef.current.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const t = ratio * duration;
    if (mediaRef.current) mediaRef.current.currentTime = t;
    setCurrentTime(t);
  }

  function skip(delta: number) {
    if (mediaRef.current) {
      mediaRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + delta));
    }
  }

  const isVideo = item.file_type === "video";
  const progress = duration ? (currentTime / duration) * 100 : 0;

  return (
    <div className="flex flex-col lg:w-7/12 xl:w-8/12 bg-gray-950 border-b lg:border-b-0 lg:border-r border-gray-800">
      {/* Media element */}
      <div className="flex-1 flex items-center justify-center bg-black min-h-[200px] max-h-[60vh] lg:max-h-none">
        {isVideo ? (
          <video
            ref={mediaRef}
            src={fileUrl}
            className="w-full h-full object-contain"
            onTimeUpdate={onTimeUpdate}
            onLoadedMetadata={onLoadedMetadata}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
          />
        ) : (
          <div className="flex flex-col items-center gap-6 p-10">
            <div className="w-32 h-32 rounded-full bg-gray-800 flex items-center justify-center">
              <Volume2 className="w-16 h-16 text-gray-500" />
            </div>
            <p className="text-gray-400 text-sm text-center max-w-sm truncate">{item.original_filename}</p>
            <audio
              ref={mediaRef}
              src={fileUrl}
              onTimeUpdate={onTimeUpdate}
              onLoadedMetadata={onLoadedMetadata}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
            />
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="bg-gray-900 border-t border-gray-800 px-4 py-3">
        {/* Progress bar */}
        <div
          ref={progressRef}
          className="w-full h-1.5 bg-gray-700 rounded-full mb-3 cursor-pointer group"
          onClick={seek}
        >
          <div
            className="h-full bg-blue-500 rounded-full relative"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Playback buttons */}
          <button onClick={() => skip(-10)} className="text-gray-400 hover:text-white transition-colors">
            <SkipBack className="w-4 h-4" />
          </button>
          <button
            onClick={togglePlay}
            className="w-9 h-9 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center text-white transition-colors"
          >
            {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>
          <button onClick={() => skip(10)} className="text-gray-400 hover:text-white transition-colors">
            <SkipForward className="w-4 h-4" />
          </button>

          {/* Time */}
          <span className="text-xs text-gray-400 tabular-nums">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          <div className="flex-1" />

          {/* Volume */}
          <button
            onClick={() => {
              setMuted(!muted);
              if (mediaRef.current) mediaRef.current.muted = !muted;
            }}
            className="text-gray-400 hover:text-white transition-colors"
          >
            {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={muted ? 0 : volume}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setVolume(v);
              setMuted(false);
              if (mediaRef.current) {
                mediaRef.current.volume = v;
                mediaRef.current.muted = false;
              }
            }}
            className="w-20 accent-blue-500"
          />
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-gray-900 border-t border-gray-800 px-4 py-2.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        {item.origin_date && (
          <span>Origin: {format(new Date(item.origin_date), "MMM d, yyyy")}</span>
        )}
        <span>Uploaded: {format(new Date(item.upload_date), "MMM d, yyyy h:mm a")}</span>
        {item.tags.length > 0 && (
          <span className="flex items-center gap-1">
            <TagIcon className="w-3 h-3" />
            {item.tags.map((t) => t.name).join(", ")}
          </span>
        )}
      </div>
    </div>
  );
}
