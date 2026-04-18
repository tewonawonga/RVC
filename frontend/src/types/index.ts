export interface Tag {
  id: number;
  name: string;
}

export interface TranscriptSegment {
  id: number;
  segment_index: number;
  start_time: number;
  end_time: number;
  text: string;
}

export type TranscriptionStatus = "pending" | "processing" | "complete" | "failed";

export interface MediaSummary {
  id: string;
  filename: string;
  original_filename: string;
  file_type: "audio" | "video";
  mime_type: string | null;
  file_size: number | null;
  duration: number | null;
  origin_date: string | null;
  upload_date: string;
  transcription_status: TranscriptionStatus;
  tags: Tag[];
}

export interface MediaDetail extends MediaSummary {
  transcript_segments: TranscriptSegment[];
}

export interface Clip {
  id: string;
  media_id: string;
  title: string;
  start_time: number;
  end_time: number;
  file_path: string | null;
  created_at: string;
}

export interface SearchParams {
  q?: string;
  tags?: string;
  origin_from?: string;
  origin_to?: string;
  upload_from?: string;
  upload_to?: string;
  file_type?: string;
  sort_by?: string;
  sort_dir?: string;
}
