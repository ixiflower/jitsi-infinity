"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface Video {
  id: number; title: string; playerUrl: string; hlsUrl: string; thumbnailUrl?: string;
  visible: number; createdAt: string;
}

export default function AdminDashboard() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [title, setTitle] = useState("");
  const [playerUrl, setPlayerUrl] = useState("");
  const [hlsUrl, setHlsUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [editVideo, setEditVideo] = useState<Video | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editThumb, setEditThumb] = useState("");
  const router = useRouter();

  const fetchVideos = useCallback(async () => {
    const res = await fetch("/api/videos");
    if (res.status === 401) { router.push("/admin/login"); return; }
    if (res.ok) setVideos(await res.json());
    setLoading(false);
  }, [router]);

  useEffect(() => { fetchVideos(); }, [fetchVideos]);

  const addVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !playerUrl.trim()) return;
    const res = await fetch("/api/videos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title.trim(), playerUrl: playerUrl.trim(), hlsUrl: hlsUrl.trim() }),
    });
    if (res.status === 401) { router.push("/admin/login"); return; }
    if (res.ok) { setTitle(""); setPlayerUrl(""); setHlsUrl(""); fetchVideos(); }
  };

  const toggleVideo = async (id: number) => {
    const res = await fetch(`/api/videos/${id}`, { method: "PATCH" });
    if (res.ok) fetchVideos();
  };

  const deleteVideo = async (id: number) => {
    if (!confirm("Delete this video permanently?")) return;
    const res = await fetch(`/api/videos/${id}`, { method: "DELETE" });
    if (res.ok) fetchVideos();
  };

  const syncNow = async () => {
    setSyncing(true);
    setSyncMsg("");
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const data = await res.json();
      setSyncMsg(data.success ? "Sync complete!" : `Error: ${data.error}`);
      if (data.success) fetchVideos();
    } catch { setSyncMsg("Sync failed"); }
    setSyncing(false);
  };

  const uploadThumb = async (videoId: number) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) return;
      const { url } = await res.json();
      await fetch(`/api/videos/${videoId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thumbnail_url: url }),
      });
      fetchVideos();
    };
    input.click();
  };

  const openEdit = (v: Video) => {
    setEditVideo(v);
    setEditTitle(v.title);
    setEditThumb(v.thumbnailUrl || "");
  };

  const saveEdit = async () => {
    if (!editVideo) return;
    const body: Record<string, string> = { title: editTitle };
    if (editThumb) body.thumbnail_url = editThumb;
    const res = await fetch(`/api/videos/${editVideo.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) { setEditVideo(null); fetchVideos(); }
  };

  const logout = async () => {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
  };

  const visible = videos.filter((v) => v.visible).length;
  const hidden = videos.filter((v) => !v.visible).length;

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage your video content</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/" className="px-4 py-2 rounded-lg text-sm font-medium bg-white/[0.06] text-zinc-300 hover:bg-white/[0.12] transition-all">
            View Site
          </Link>
          <button onClick={logout} className="px-4 py-2 rounded-lg text-sm font-medium bg-red-950/50 border border-red-800/50 text-red-400 hover:bg-red-950/70 transition-all">
            Logout
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4 mb-8">
        {[
          { label: "Total Videos", value: videos.length, color: "text-violet-400", bg: "bg-violet-600/10" },
          { label: "Visible", value: visible, color: "text-emerald-400", bg: "bg-emerald-600/10" },
          { label: "Hidden", value: hidden, color: "text-amber-400", bg: "bg-amber-600/10" },
          { label: "Sync Status", value: syncMsg || "Idle", color: "text-cyan-400", bg: "bg-cyan-600/10", isText: true },
        ].map((stat) => (
          <div key={stat.label} className={`${stat.bg} border border-white/[0.06] rounded-xl p-5`}>
            <p className="text-3xl font-bold mb-1">
              <span className={stat.color}>{stat.isText ? "" : stat.value}</span>
              {stat.isText && <span className="text-sm font-normal text-zinc-400">{stat.value}</span>}
            </p>
            <p className="text-sm text-zinc-500">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Actions bar */}
      <div className="flex flex-wrap gap-3 mb-8">
        <button onClick={syncNow} disabled={syncing}
          className="px-5 py-2.5 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition-colors flex items-center gap-2">
          {syncing ? (
            <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/> Syncing...</>
          ) : "Sync Now"}
        </button>
      </div>

      {/* Add Video Form */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 mb-8">
        <h2 className="text-sm font-semibold text-zinc-300 mb-4 uppercase tracking-wider">Add New Video</h2>
        <form onSubmit={addVideo} className="flex flex-wrap gap-3">
          <input type="text" placeholder="Video title" value={title} onChange={(e) => setTitle(e.target.value)}
            className="flex-1 min-w-[200px] bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" required />
          <input type="url" placeholder="Player URL" value={playerUrl} onChange={(e) => setPlayerUrl(e.target.value)}
            className="flex-[2] min-w-[280px] bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" required />
          <input type="url" placeholder="HLS URL (optional)" value={hlsUrl} onChange={(e) => setHlsUrl(e.target.value)}
            className="flex-[2] min-w-[280px] bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" />
          <button type="submit" className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors shrink-0">
            Add Video
          </button>
        </form>
      </div>

      {/* Video List */}
      {loading ? (
        <div className="flex justify-center py-16"><div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin"/></div>
      ) : videos.length === 0 ? (
        <div className="text-center py-16 text-zinc-600">No videos yet. Add one above or sync from ArvanCloud.</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {videos.map((v) => (
            <div key={v.id} className={`flex gap-4 p-4 rounded-xl border transition-all ${
              v.visible ? "bg-white/[0.02] border-white/[0.06]" : "bg-white/[0.01] border-white/[0.04] opacity-60"
            }`}>
              {/* Thumbnail */}
              <div className="w-28 shrink-0 aspect-video rounded-lg overflow-hidden bg-zinc-800">
                {v.thumbnailUrl ? (
                  <img src={v.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-violet-600/40 to-purple-700/40 flex items-center justify-center">
                    <svg className="w-6 h-6 text-white/30" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </div>
                )}
              </div>
              {/* Info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-zinc-200 truncate">{v.title}</h3>
                <p className="text-xs text-zinc-600 truncate mt-0.5">{v.playerUrl}</p>
                <p className="text-xs text-zinc-700 mt-0.5">ID: {v.id} · {new Date(v.createdAt).toLocaleDateString()}</p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    v.visible ? "bg-emerald-600/20 text-emerald-400" : "bg-amber-600/20 text-amber-400"
                  }`}>{v.visible ? "Visible" : "Hidden"}</span>
                  <button onClick={() => toggleVideo(v.id)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.06] text-zinc-400 hover:bg-white/[0.12] hover:text-white transition-all">
                    {v.visible ? "Hide" : "Show"}
                  </button>
                  <button onClick={() => openEdit(v)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.06] text-zinc-400 hover:bg-white/[0.12] hover:text-white transition-all">
                    Edit
                  </button>
                  <button onClick={() => uploadThumb(v.id)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.06] text-zinc-400 hover:bg-white/[0.12] hover:text-white transition-all">
                    Thumbnail
                  </button>
                  <button onClick={() => deleteVideo(v.id)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-950/30 text-red-400 hover:bg-red-950/50 transition-all">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {editVideo && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setEditVideo(null)}>
          <div className="bg-zinc-900 border border-white/[0.08] rounded-2xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-zinc-100 mb-4">Edit Video</h3>
            <div className="space-y-3">
              <input type="text" placeholder="Title" value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                className="w-full bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" />
              <input type="text" placeholder="Thumbnail URL" value={editThumb} onChange={(e) => setEditThumb(e.target.value)}
                className="w-full bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" />
              {editThumb && (
                <img src={editThumb} alt="" className="w-full aspect-video object-cover rounded-lg" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setEditVideo(null)} className="px-4 py-2 rounded-lg text-sm font-medium bg-white/[0.06] text-zinc-400 hover:bg-white/[0.12] transition-all">
                Cancel
              </button>
              <button onClick={saveEdit} className="px-4 py-2 rounded-lg text-sm font-medium bg-violet-600 hover:bg-violet-500 text-white transition-all">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
