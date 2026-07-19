"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

type Video = {
  id: number;
  title: string;
  playerUrl: string;
  hlsUrl: string;
  visible: number;
  createdAt: string;
};

export default function AdminDashboardPage() {
  const router = useRouter();

  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed] = useState(false);

  // Add video form
  const [title, setTitle] = useState("");
  const [playerUrl, setPlayerUrl] = useState("");
  const [hlsUrl, setHlsUrl] = useState("");
  const [addError, setAddError] = useState("");
  const [adding, setAdding] = useState(false);

  // Fetch videos
  const fetchVideos = useCallback(async () => {
    try {
      const res = await fetch("/api/videos");
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
      const data: Video[] = await res.json();
      setVideos(data);
      setAuthed(true);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  // Add video
  const addVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !playerUrl.trim()) {
      setAddError("Title and Player URL are required.");
      return;
    }
    setAdding(true);
    setAddError("");
    try {
      const res = await fetch("/api/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          player_url: playerUrl.trim(),
          hls_url: hlsUrl.trim(),
        }),
      });
      if (res.ok) {
        const newVideo: Video = await res.json();
        setVideos((prev) => [newVideo, ...prev]);
        setTitle("");
        setPlayerUrl("");
        setHlsUrl("");
      } else {
        const err = await res.json();
        setAddError(err.error || "Failed to add video.");
      }
    } catch {
      setAddError("Network error.");
    } finally {
      setAdding(false);
    }
  };

  // Toggle visibility
  const toggleVisibility = async (id: number) => {
    try {
      const res = await fetch(`/api/videos/${id}`, { method: "PATCH" });
      if (res.ok) {
        const updated: Video = await res.json();
        setVideos((prev) => prev.map((v) => (v.id === id ? updated : v)));
      }
    } catch {
      // ignore
    }
  };

  // Delete video
  const deleteVideo = async (id: number) => {
    if (!confirm("Delete this video and all its likes/comments?")) return;
    try {
      const res = await fetch(`/api/videos/${id}`, { method: "DELETE" });
      if (res.ok) {
        setVideos((prev) => prev.filter((v) => v.id !== id));
      }
    } catch {
      // ignore
    }
  };

  // Logout
  const logout = async () => {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
  };

  // Stats
  const total = videos.length;
  const visible = videos.filter((v) => v.visible).length;
  const hidden = total - visible;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="flex items-center gap-3 text-zinc-400">
          <svg
            className="h-5 w-5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12" cy="12" r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-sm text-zinc-400 hover:text-violet-400">
              ← Home
            </Link>
            <h1 className="text-xl font-bold text-violet-400">
              Admin Dashboard
            </h1>
          </div>
          <button
            onClick={logout}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:border-red-700 hover:text-red-400"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        {/* Stats */}
        <div className="mb-10 grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-sm text-zinc-500">Total</p>
            <p className="text-2xl font-bold text-zinc-100">{total}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-sm text-zinc-500">Visible</p>
            <p className="text-2xl font-bold text-green-400">{visible}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-sm text-zinc-500">Hidden</p>
            <p className="text-2xl font-bold text-yellow-400">{hidden}</p>
          </div>
        </div>

        {/* Add video form */}
        <div className="mb-10 rounded-2xl border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="mb-4 text-lg font-semibold text-zinc-200">
            Add New Video
          </h2>
          <form onSubmit={addVideo} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-400">
                  Title *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Video title"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-400">
                  Player URL *
                </label>
                <input
                  type="url"
                  value={playerUrl}
                  onChange={(e) => setPlayerUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-400">
                HLS URL
              </label>
              <input
                type="url"
                value={hlsUrl}
                onChange={(e) => setHlsUrl(e.target.value)}
                placeholder="https://... (optional)"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
            {addError && (
              <p className="text-sm text-red-400">{addError}</p>
            )}
            <button
              type="submit"
              disabled={adding}
              className="rounded-lg bg-violet-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              {adding ? "Adding..." : "Add Video"}
            </button>
          </form>
        </div>

        {/* Videos list */}
        <h2 className="mb-4 text-lg font-semibold text-zinc-200">
          All Videos ({total})
        </h2>
        {videos.length === 0 ? (
          <p className="text-sm text-zinc-500">No videos yet.</p>
        ) : (
          <div className="space-y-3">
            {videos.map((v) => (
              <div
                key={v.id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4 sm:flex-nowrap"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-zinc-100 truncate">
                      {v.title}
                    </h3>
                    {v.visible ? (
                      <span className="shrink-0 rounded-full bg-green-900/60 px-2 py-0.5 text-xs text-green-400">
                        Visible
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full bg-yellow-900/60 px-2 py-0.5 text-xs text-yellow-400">
                        Hidden
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500 truncate">
                    {v.playerUrl}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleVisibility(v.id)}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-violet-600 hover:text-violet-400"
                  >
                    {v.visible ? "Hide" : "Show"}
                  </button>
                  <button
                    onClick={() => deleteVideo(v.id)}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-red-700 hover:text-red-400"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
