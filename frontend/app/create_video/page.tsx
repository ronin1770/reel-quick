"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ChangeEvent } from "react";

type VideoPart = {
  id: string;
  fileName: string;
  fileLocation: string;
  start: number;
  end: number;
  selectedDuration: number;
  synced: boolean;
  backendId?: string;
};

type UploadStatus = "uploading" | "ready" | "error";

type VideoFile = {
  id: string;
  file: File;
  location: string | null;
  status: UploadStatus;
  error?: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const formatTime = (value: number) => {
  if (!Number.isFinite(value)) return "0:00";
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

const formatHms = (value: number) => {
  if (!Number.isFinite(value)) return "00:00:00";
  const total = Math.max(0, Math.floor(value));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};

const buildFileId = (file: File) =>
  `${file.name}-${file.lastModified}-${Math.random().toString(16).slice(2)}`;

const getErrorMessage = async (response: Response) => {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((item: { msg?: string }) => item?.msg)
        .filter(Boolean)
        .join(", ");
    }
  } catch (error) {
    return null;
  }
  return null;
};

export default function CreateVideoPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [videoTitle, setVideoTitle] = useState("");
  const [videoDescription, setVideoDescription] = useState("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [files, setFiles] = useState<VideoFile[]>([]);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(0);
  const [parts, setParts] = useState<VideoPart[]>([]);
  const [isCreatingVideo, setIsCreatingVideo] = useState(false);
  const [isAddingPart, setIsAddingPart] = useState(false);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const [isEnqueued, setIsEnqueued] = useState(false);
  const [videoErrors, setVideoErrors] = useState<{ title?: string }>({});
  const [partErrors, setPartErrors] = useState<{
    video?: string;
    timeline?: string;
    upload?: string;
  }>({});
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeFile = activeIndex !== null ? files[activeIndex] : null;

  useEffect(() => {
    if (!activeFile) {
      setPreviewUrl(null);
      setDuration(0);
      setStartTime(0);
      setEndTime(0);
      return;
    }

    const url = URL.createObjectURL(activeFile.file);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [activeFile]);

  useEffect(() => {
    if (files.length === 0) {
      setActiveIndex(null);
      return;
    }

    if (activeIndex === null || activeIndex >= files.length) {
      setActiveIndex(0);
    }
  }, [files, activeIndex]);

  useEffect(() => {
    if (duration <= 0) return;
    if (endTime === 0 || endTime > duration) {
      setEndTime(duration);
    }
    if (startTime > duration) {
      setStartTime(0);
    }
  }, [duration, endTime, startTime]);

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const handlePendingFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const selection = Array.from(event.target.files ?? []);
    setPendingFiles(selection);
  };

  const uploadFile = async (item: VideoFile) => {
    try {
      const formData = new FormData();
      formData.append("file", item.file);

      const response = await fetch(`${API_BASE}/uploads`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const detail = await getErrorMessage(response);
        throw new Error(detail ?? `Upload failed (${response.status})`);
      }

      const data = (await response.json()) as { file_location?: string };
      if (!data.file_location) {
        throw new Error("Upload succeeded without a file_location.");
      }

      setFiles((prev) =>
        prev.map((file) =>
          file.id === item.id
            ? {
                ...file,
                location: data.file_location,
                status: "ready",
                error: undefined,
              }
            : file
        )
      );

      return { success: true, name: item.file.name };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to upload file.";
      setFiles((prev) =>
        prev.map((file) =>
          file.id === item.id
            ? {
                ...file,
                status: "error",
                error: message,
              }
            : file
        )
      );
      return { success: false, name: item.file.name };
    }
  };

  const handleAddFiles = async () => {
    if (pendingFiles.length === 0 || isUploadingFiles) return;
    setErrorMessage(null);
    setStatusMessage(null);

    const nextFiles: VideoFile[] = pendingFiles.map((file) => ({
      id: buildFileId(file),
      file,
      location: null,
      status: "uploading",
    }));
    const startingIndex = files.length;

    setFiles((prev) => [...prev, ...nextFiles]);
    if (activeIndex === null && nextFiles.length > 0) {
      setActiveIndex(startingIndex);
    }

    setPendingFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    setIsUploadingFiles(true);
    const results = await Promise.all(nextFiles.map(uploadFile));
    setIsUploadingFiles(false);

    const failed = results.filter((result) => !result.success);
    if (failed.length > 0) {
      setErrorMessage(
        `Upload failed for: ${failed.map((item) => item.name).join(", ")}`
      );
    } else if (results.length > 0) {
      setStatusMessage(`Uploaded ${results.length} file(s).`);
    }
  };

  const handleRemoveFile = (index: number) => {
    const fileName = files[index]?.file.name;
    setFiles((prev) => prev.filter((_, i) => i !== index));
    if (fileName) {
      setParts((prev) => prev.filter((part) => part.fileName !== fileName));
      setIsEnqueued(false);
    }
    setActiveIndex((prev) => {
      if (prev === null) return prev;
      if (prev === index) return null;
      if (prev > index) return prev - 1;
      return prev;
    });
  };

  const handleStartChange = (value: number) => {
    if (value > endTime) {
      setStartTime(endTime);
      return;
    }
    setStartTime(value);
  };

  const handleEndChange = (value: number) => {
    if (value < startTime) {
      setEndTime(startTime);
      return;
    }
    setEndTime(value);
  };

  const syncQueuedParts = async (targetVideoId: string) => {
    const snapshot = parts;
    if (snapshot.length === 0) return;

    for (let index = 0; index < snapshot.length; index += 1) {
      const part = snapshot[index];
      if (part.synced) continue;

      const payload = {
        video_id: targetVideoId,
        file_part_name: part.fileName,
        part_number: index + 1,
        file_location: part.fileLocation,
        start_time: formatHms(part.start),
        end_time: formatHms(part.end),
        selected_duration: part.selectedDuration,
        active: true,
      };

      const response = await fetch(`${API_BASE}/video-parts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await getErrorMessage(response);
        throw new Error(detail ?? `Add part failed (${response.status})`);
      }

      const data = (await response.json()) as { video_parts_id?: string };
      setParts((prev) =>
        prev.map((item) =>
          item.id === part.id
            ? {
                ...item,
                synced: true,
                backendId: data.video_parts_id ?? item.backendId,
              }
            : item
        )
      );
    }
  };

  const enqueueVideo = async (targetVideoId: string) => {
    const response = await fetch(`${API_BASE}/videos/${targetVideoId}/enqueue`, {
      method: "POST",
    });

    if (!response.ok) {
      const detail = await getErrorMessage(response);
      throw new Error(detail ?? `Enqueue video failed (${response.status})`);
    }
  };

  const handleCreateVideo = async () => {
    setVideoErrors({});
    setErrorMessage(null);
    setStatusMessage(null);

    const trimmedTitle = videoTitle.trim();
    if (!trimmedTitle) {
      setVideoErrors({ title: "Video title is required." });
      return;
    }

    setIsCreatingVideo(true);
    try {
      const createdNow = !videoId;
      let nextVideoId = videoId;

      if (!nextVideoId) {
        const payload: Record<string, unknown> = {
          video_title: trimmedTitle,
          active: true,
        };
        const trimmedDescription = videoDescription.trim();
        if (trimmedDescription) {
          payload.video_introduction = trimmedDescription;
        }

        const response = await fetch(`${API_BASE}/videos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const detail = await getErrorMessage(response);
          throw new Error(detail ?? `Create video failed (${response.status})`);
        }

        const data = (await response.json()) as { video_id?: string };
        if (!data.video_id) {
          throw new Error("Create video succeeded without a video_id.");
        }

        nextVideoId = data.video_id;
        setVideoId(nextVideoId);
      }

      const hasQueuedParts = parts.some((part) => !part.synced);
      if (hasQueuedParts) {
        await syncQueuedParts(nextVideoId);
      }

      await enqueueVideo(nextVideoId);
      setIsEnqueued(true);

      if (createdNow && hasQueuedParts) {
        setStatusMessage("Video created, parts saved, and queued.");
      } else if (createdNow) {
        setStatusMessage("Video created and queued.");
      } else if (hasQueuedParts) {
        setStatusMessage("Parts saved and video queued.");
      } else {
        setStatusMessage("Video queued.");
      }

      router.push("/videos");
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to create or queue video."
      );
    } finally {
      setIsCreatingVideo(false);
    }
  };

  const handleAddPart = async () => {
    setPartErrors({});
    setErrorMessage(null);
    setStatusMessage(null);

    const trimmedTitle = videoTitle.trim();
    if (!trimmedTitle) {
      setVideoErrors({ title: "Video title is required." });
      setPartErrors({
        video: "Add a video title before adding parts.",
      });
      return;
    }

    if (!activeFile || duration <= 0) {
      setPartErrors({
        video: "Select a clip to add a part.",
      });
      return;
    }

    if (activeFile.status === "uploading") {
      setPartErrors({
        upload: "Upload in progress. Please wait.",
      });
      return;
    }

    if (activeFile.status === "error" || !activeFile.location) {
      setPartErrors({
        upload: "Upload the clip before adding a part.",
      });
      return;
    }

    if (endTime <= startTime) {
      setPartErrors({
        timeline: "Select a valid start/end range.",
      });
      return;
    }

    setIsAddingPart(true);
    const selectedDuration = Math.max(0, endTime - startTime);
    const partId = `${activeFile.file.name}-${Date.now()}`;

    setParts((prev) => [
      ...prev,
      {
        id: partId,
        fileName: activeFile.file.name,
        fileLocation: activeFile.location,
        start: startTime,
        end: endTime,
        selectedDuration: Number(selectedDuration.toFixed(2)),
        synced: false,
      },
    ]);
    setIsEnqueued(false);
    setStatusMessage("Part queued. Save it with Create Video.");
    setIsAddingPart(false);
  };

  const pendingLabel = pendingFiles.length
    ? `${pendingFiles.length} file(s) selected`
    : "No file chosen";

  const timelineFill =
    duration > 0
      ? {
          left: `${(startTime / duration) * 100}%`,
          width: `${((endTime - startTime) / duration) * 100}%`,
        }
      : { left: "0%", width: "0%" };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <span className="neon-pill">Studio</span>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Build your reel
            </h1>
            <p className="text-muted">
              Craft a tight sequence from your clips, then stack each trimmed
              moment into a publish-ready reel.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="neon-chip">{files.length} clip(s)</span>
            <span className="neon-chip">{parts.length} part(s)</span>
            <span className="neon-chip max-w-[220px] truncate">
              Active: {activeFile ? activeFile.file.name : "None"}
            </span>
            {videoId && (
              <span className="neon-chip max-w-[220px] truncate">
                Video ID: {videoId}
              </span>
            )}
          </div>
        </div>
      </section>

      {(statusMessage || errorMessage) && (
        <div
          className={`neon-card rounded-2xl px-4 py-3 text-sm ${
            errorMessage ? "text-rose-200" : "text-emerald-200"
          }`}
        >
          {errorMessage ?? statusMessage}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="space-y-6">
          <div className="neon-panel rounded-3xl p-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-[180px_1fr] items-start">
              <label className="pt-2 text-sm font-semibold text-soft">
                Video Title
              </label>
              <div className="space-y-2">
                <input
                  className="neon-input"
                  placeholder="Enter a title"
                  type="text"
                  value={videoTitle}
                  onChange={(event) => setVideoTitle(event.target.value)}
                />
                {videoErrors.title && (
                  <p className="text-xs text-rose-200">{videoErrors.title}</p>
                )}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-[180px_1fr] items-start">
              <label className="pt-2 text-sm font-semibold text-soft">
                Video Description
              </label>
              <textarea
                className="neon-input neon-textarea"
                placeholder="Short description for the reel"
                value={videoDescription}
                onChange={(event) => setVideoDescription(event.target.value)}
              />
            </div>
          </div>

          <div className="neon-panel rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
                Preview
              </p>
              <span className="neon-badge">
                {duration > 0 ? `${formatTime(duration)} total` : "No duration"}
              </span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
              {previewUrl ? (
                <video
                  ref={videoRef}
                  className="aspect-video w-full rounded-xl bg-black"
                  controls
                  onLoadedMetadata={(event) => {
                    const nextDuration = event.currentTarget.duration || 0;
                    setDuration(nextDuration);
                  }}
                  src={previewUrl}
                />
              ) : (
                <div className="flex aspect-video w-full items-center justify-center rounded-xl bg-black/60 text-sm text-muted">
                  Select a video to preview
                </div>
              )}
            </div>
            <div className="grid gap-3 md:grid-cols-[180px_1fr] items-start">
              <label className="pt-2 text-sm font-semibold text-soft">
                Upload Status
              </label>
              <div className="space-y-2">
                <div className="neon-card rounded-xl px-3 py-2 text-xs text-muted">
                  {activeFile
                    ? activeFile.status === "ready"
                      ? "Uploaded"
                      : activeFile.status === "uploading"
                      ? "Uploading..."
                      : "Upload failed"
                    : "No clip selected"}
                </div>
                {activeFile?.status === "error" && activeFile.error && (
                  <p className="text-xs text-rose-200">{activeFile.error}</p>
                )}
                {partErrors.upload && (
                  <p className="text-xs text-rose-200">{partErrors.upload}</p>
                )}
              </div>
            </div>
            <div className="relative h-10 rounded-full border border-white/10 bg-[rgba(10,6,24,0.9)]">
              <div
                className="absolute inset-y-1 rounded-full bg-gradient-to-r from-[#ff2dc7] via-[#8b4dff] to-[#28f6ff]"
                style={timelineFill}
              />
              <div className="absolute inset-0 flex items-center justify-center text-[10px] font-semibold uppercase tracking-[0.4em] text-soft">
                Video timeline
              </div>
            </div>
            {partErrors.timeline && (
              <p className="text-xs text-rose-200">{partErrors.timeline}</p>
            )}
            {partErrors.video && (
              <p className="text-xs text-rose-200">{partErrors.video}</p>
            )}
          </div>

          <div className="neon-panel rounded-3xl p-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-[180px_1fr] items-center">
              <label className="text-sm font-semibold text-soft">Start Time</label>
              <div className="flex items-center gap-4">
                <input
                  className="neon-input h-10 w-20 px-2 text-center text-xs font-semibold"
                  readOnly
                  value={formatTime(startTime)}
                />
                <input
                  className="neon-range w-full"
                  max={duration || 0}
                  min={0}
                  onChange={(event) =>
                    handleStartChange(Number(event.target.value))
                  }
                  step={0.1}
                  type="range"
                  value={startTime}
                  disabled={!activeFile || duration <= 0}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-[180px_1fr] items-center">
              <label className="text-sm font-semibold text-soft">End Time</label>
              <div className="flex items-center gap-4">
                <input
                  className="neon-input h-10 w-20 px-2 text-center text-xs font-semibold"
                  readOnly
                  value={formatTime(endTime)}
                />
                <input
                  className="neon-range w-full"
                  max={duration || 0}
                  min={0}
                  onChange={(event) =>
                    handleEndChange(Number(event.target.value))
                  }
                  step={0.1}
                  type="range"
                  value={endTime}
                  disabled={!activeFile || duration <= 0}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                className="neon-button neon-button-primary"
                type="button"
                onClick={handleAddPart}
                disabled={!activeFile || duration <= 0 || isAddingPart}
              >
                {isAddingPart ? "Adding..." : "Add Part"}
              </button>
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <div className="neon-panel rounded-3xl p-5 space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Add Files
            </h2>
            <div className="flex flex-col gap-3">
              <div className="neon-card rounded-xl px-3 py-2 text-xs text-muted">
                {pendingLabel}
              </div>
              <div className="flex items-center gap-3">
                <button
                  className="neon-button neon-button-ghost px-4 py-2 text-xs"
                  type="button"
                  onClick={handleBrowse}
                >
                  Browse
                </button>
                <button
                  className="neon-button px-4 py-2 text-xs"
                  type="button"
                  onClick={handleAddFiles}
                  disabled={pendingFiles.length === 0 || isUploadingFiles}
                >
                  {isUploadingFiles ? "Uploading..." : "Add"}
                </button>
              </div>
              <p className="text-xs text-soft">
                Files upload automatically so the backend can process them.
              </p>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept="video/*"
                multiple
                onChange={handlePendingFiles}
              />
            </div>
          </div>

          <div className="neon-panel rounded-3xl p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Selected Files
            </h3>
            <ol className="space-y-3 text-sm text-muted">
              {files.length === 0 && <li className="text-soft">No files selected.</li>}
              {files.map((item, index) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2"
                >
                  <button
                    className={`text-left text-xs font-semibold ${
                      activeIndex === index ? "text-white" : "text-muted"
                    }`}
                    type="button"
                    onClick={() => setActiveIndex(index)}
                  >
                    {index + 1}. {item.file.name}
                    <span className="block text-[10px] text-soft">
                      {item.status === "ready"
                        ? "Uploaded"
                        : item.status === "uploading"
                        ? "Uploading..."
                        : "Upload failed"}
                    </span>
                  </button>
                  <button
                    className="flex h-7 w-7 items-center justify-center rounded-full border border-red-400/40 text-[10px] font-bold text-red-300"
                    type="button"
                    onClick={() => handleRemoveFile(index)}
                  >
                    x
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <div className="neon-panel rounded-3xl p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Added Parts
            </h3>
            <ol className="space-y-3 text-sm text-muted">
              {parts.length === 0 && <li className="text-soft">No parts added.</li>}
              {parts.map((part, index) => (
                <li
                  key={part.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2"
                >
                  <span className="text-xs">
                    {index + 1}. {part.fileName}
                    <span className="block text-[11px] text-soft">
                      ({formatTime(part.start)} - {formatTime(part.end)})
                    </span>
                  </span>
                  <button
                    className="flex h-7 w-7 items-center justify-center rounded-full border border-red-400/40 text-[10px] font-bold text-red-300"
                    type="button"
                    onClick={() => {
                      setParts((prev) => prev.filter((item) => item.id !== part.id));
                      setIsEnqueued(false);
                    }}
                  >
                    x
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <div className="neon-panel rounded-3xl p-5 space-y-3">
            <button
              className="neon-button neon-button-primary w-full"
              type="button"
              onClick={handleCreateVideo}
              disabled={
                isCreatingVideo ||
                (Boolean(videoId) && parts.every((part) => part.synced) && isEnqueued)
              }
            >
              {isCreatingVideo
                ? "Creating..."
                : videoId
                ? parts.some((part) => !part.synced)
                  ? "Save Parts"
                  : "Video Created"
                : "Create Video"}
            </button>
            <Link className="neon-button neon-button-ghost w-full" href="/">
              Cancel
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
