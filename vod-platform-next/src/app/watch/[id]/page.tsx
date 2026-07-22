"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Video {
  id: string | number; title: string; playerUrl: string; hlsUrl: string; thumbnailUrl?: string;
  createdAt: string; likeCount: number; commentCount: number;
}
interface Comment { id: number; username: string; text: string; createdAt: string; }

export default function WatchPage() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [moreVideos, setMoreVideos] = useState<Video[]>([]);
  const [commentName, setCommentName] = useState("");
  const [commentText, setCommentText] = useState("");
  const [error, setError] = useState("");

  const videoId = id;

  const fetchVideo = useCallback(async () => {
    const res = await fetch(`/api/videos/${videoId}`);
    if (res.ok) setVideo(await res.json());
  }, [videoId]);

  const fetchComments = useCallback(async () => {
    const res = await fetch(`/api/videos/${videoId}/comments`);
    if (res.ok) setComments(await res.json());
  }, [videoId]);

  const fetchMore = useCallback(async () => {
    const res = await fetch(`/api/videos?exclude=${videoId}`);
    if (res.ok) setMoreVideos(await res.json());
  }, [videoId]);

  useEffect(() => { fetchVideo(); fetchComments(); fetchMore(); }, [fetchVideo, fetchComments, fetchMore]);

  const toggleLike = async () => {
    const res = await fetch(`/api/videos/${videoId}/like`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setLiked(data.liked);
      setLikeCount(data.count);
    }
  };

  const addComment = async () => {
    setError("");
    if (!commentText.trim()) { setError("Please write a comment."); return; }
    const res = await fetch(`/api/videos/${videoId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: commentName.trim() || "Anonymous", text: commentText.trim() }),
    });
    if (res.ok) {
      const c = await res.json();
      setComments((prev) => [c, ...prev]);
      setCommentText("");
    } else {
      const e = await res.json();
      setError(e.error || "Failed to post");
    }
  };

  const timeAgo = (date: string) => {
    const d = new Date(date);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return d.toLocaleDateString();
  };

  if (!video) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin"/>
      </div>
    );
  }

  return (
    <div className="max-w-[1720px] mx-auto px-4 sm:px-6 py-6">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main column */}
        <div className="flex-1 min-w-0">
          {/* Video player */}
          <div className="relative aspect-video rounded-2xl overflow-hidden bg-black border border-white/[0.06] shadow-2xl">
            <iframe src={video.playerUrl} allowFullScreen className="absolute inset-0 w-full h-full"/>
          </div>

          {/* Title & actions */}
          <h1 className="text-xl sm:text-2xl font-bold mt-4 text-zinc-100">{video.title}</h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
            <span>{new Date(video.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
          </div>

          {/* Action bar */}
          <div className="flex items-center gap-2 mt-4 pb-4 border-b border-white/[0.06]">
            <button
              onClick={toggleLike}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                liked
                  ? "bg-violet-600/20 text-violet-400 border border-violet-600/40"
                  : "bg-white/[0.06] text-zinc-300 hover:bg-white/[0.12]"
              }`}
            >
              <svg className="w-5 h-5" fill={liked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
              </svg>
              {likeCount || video.likeCount}
            </button>
          </div>

          {/* Comments */}
          <div className="mt-6">
            <h2 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              {comments.length} Comments
            </h2>

            {/* Add comment */}
            <div className="flex gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 shrink-0 flex items-center justify-center text-sm font-bold">U</div>
              <div className="flex-1 min-w-0">
                {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
                <input
                  type="text" placeholder="Your name..." value={commentName} onChange={(e) => setCommentName(e.target.value)}
                  className="w-full bg-white/[0.06] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50 mb-2"
                  maxLength={50}
                />
                <div className="flex gap-2">
                  <input
                    type="text" placeholder="Add a comment..." value={commentText} onChange={(e) => setCommentText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addComment()}
                    className="flex-1 bg-white/[0.06] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"
                    maxLength={500}
                  />
                  <button onClick={addComment} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors shrink-0">
                    Comment
                  </button>
                </div>
              </div>
            </div>

            {/* Comment list */}
            <div className="space-y-4">
              {comments.length === 0 && (
                <p className="text-zinc-600 text-sm text-center py-8">No comments yet. Be the first!</p>
              )}
              {comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-white/[0.08] shrink-0 flex items-center justify-center text-sm font-bold text-zinc-400">
                    {c.username[0].toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-300">@{c.username}</span>
                      <span className="text-xs text-zinc-600">{timeAgo(c.createdAt)}</span>
                    </div>
                    <p className="text-sm text-zinc-400 mt-1 whitespace-pre-wrap break-words">{c.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:w-[360px] shrink-0">
          <div className="sticky top-[72px] max-h-[calc(100vh-90px)] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">More Videos</h3>
              <Link href="/" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">View all</Link>
            </div>
            <div className="space-y-3">
              {moreVideos.length === 0 && (
                <p className="text-zinc-600 text-sm text-center py-8">No other videos yet.</p>
              )}
              {moreVideos.map((mv) => (
                <Link key={String(mv.id)} href={`/watch/${mv.id}`} className="flex gap-3 group">
                  <div className="relative w-40 shrink-0 aspect-video rounded-lg overflow-hidden bg-zinc-800">
                    {mv.thumbnailUrl ? (
                      <img src={mv.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-violet-600/40 to-purple-700/40 flex items-center justify-center">
                        <svg className="w-6 h-6 text-white/30" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8 5v14l11-7z"/>
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-200 group-hover:text-violet-400 transition-colors line-clamp-2 leading-snug">{mv.title}</p>
                    <p className="text-xs text-zinc-600 mt-1">{new Date(mv.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
