export type OutputFormat = "mp4" | "webm" | "mp3";
export type Resolution = "360p" | "480p" | "720p" | "1080p" | "audio_only";

export interface FormatOption {
  format: OutputFormat;
  resolution: Resolution;
  is_audio_only: boolean;
  file_extension: string;
  description: string;
  approx_file_size?: number;
}

export interface VideoMetadata {
  media_id: string;
  source_url: string;
  title: string;
  thumbnail_url: string;
  duration_seconds: number;
  provider: string;
  uploader?: string;
  available_formats: FormatOption[];
}
