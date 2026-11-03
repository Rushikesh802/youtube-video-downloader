import { OutputFormat, Resolution } from "./video";

export type DownloadStatus =
  | "queued"
  | "processing"
  | "uploading"
  | "completed"
  | "failed"
  | "expired"
  | "cancelled";

export interface DownloadJob {
  id: string;
  user_id: string;
  media_id: string;
  status: DownloadStatus;
  format: OutputFormat;
  resolution: Resolution;
  progress: number;
  file_size?: number;
  error_message?: string;
  expires_at?: string;
  created_at: string;
}

export interface DownloadHistoryItem {
  id: string;
  download_id: string;
  downloaded_at: string;
  ip_hash?: string;
  format?: OutputFormat;
  resolution?: Resolution;
  file_size?: number;
  title?: string;
  thumbnail_url?: string;
  source_url?: string;
}

export interface DownloadFileResponse {
  download_url: string;
  expires_in_seconds: number;
  filename: string;
  file_size?: number;
  content_type: string;
}
