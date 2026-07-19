"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

type Video = {
  id: number;
  title: string;
  playerUrl: string;
  hlsUrl: string;
  visible: number;
  createdAt: string;
  likeCount: number;
  commentCount: number;
};

type Comment = {
  id: number;
  videoId: number;
  userToken: string;
  username: string;
  text: string;
  createdAt: string;
};

export default function WatchPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentName, setCommentName] = useState("");
  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [commentError, setCommentError] = useState("");

  // Fetch video data
  const fetchVideo = useCallback(async () => {
    try {
      const res = await fetch(`/api/videos/${id}`);
      if (!res.ok) throw new Error("Video not found");
      const data: Video = await res.json();
      setVideo(data);
      setLikeCount(data.likeCount);
    } catch (err: any) {
      setError(err.message || "Failed to load video");
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Fetch comments
  const fetchComments = useCallback(async () => {
    try {
      const res = await fetch(`/api/videos/${id}/comments`);
      if (res.ok) {
        const data: Comment[] = await res.json();
        setComments(data);
      }
    } catch {
      // Silently ignore
    }
  }, [id]);

  // Check if current user liked
  const checkLiked = useCallback(async () => {
    try {
      // We determine liked state by toggling and reading the response
      // For now, we just rely on the initial like button state being unknown
      // The API's toggle response tells us the new state
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchVideo();
    fetchComments();
  }, [fetchVideo, fetchComments]);

  // Toggle like
  const toggleLike = async () => {
    try {
      const res = await fetch(`/api/videos/${id}/like`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setLiked(data.liked);
        setLikeCount(data.count);
      }
    } catch {
      // ignore
    }
  };

  // Submit comment
  const submitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentName.trim() || !commentText.trim()) {
      setCommentError("Name and comment are required.");
      return;
    }
    setSubmitting(true);
    setCommentError("");
    try {
      const res = await fetch(`/api/videos/${id}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: commentName.trim(),
          text: commentText.trim(),
        }),
      });
      if (res.ok) {
        const newComment: Comment = await res.json();
        setComments((prev) => [newComment, ...prev]);
        setCommentName("");
        setCommentText("");
      } else {
        const err = await res.json();
        setCommentError(err.error || "Failed to post comment.");
      }
    } catch {
      setCommentError("Network error. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

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
          Loading video...
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-950">
        <p className="text-xl text-zinc-400">{error || "Video not found"}</p>
        <Link
          href="/"
          className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-violet-500"
        >
          ← Back to videos
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🎬</span>
            <h1 className="text-lg font-bold text-violet-400">VOD Platform</h1>
          </Link>
          <Link
            href="/admin/login"
            className="text-sm text-zinc-400 transition hover:text-violet-400"
          >
            Admin
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {/* Video title */}
        <h2 className="mb-6 text-2xl font-bold text-zinc-100">
          {video.title}
        </h2>

        {/* Video player iframe */}
        <div className="relative mb-6 aspect-video w-full overflow-hidden rounded-xl border border-zinc-800 bg-black">
          <iframe
            src={video.playerUrl}
            className="absolute inset-0 h-full w-full"
            allowFullScreen
            allow="autoplay; fullscreen"
            title={video.title}
          />
        </div>

        {/* Like button + stats */}
        <div className="mb-8 flex items-center gap-4">
          <button
            onClick={toggleLike}
            className={`flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition ${
              liked
                ? "border-violet-500 bg-violet-600/20 text-violet-300"
                : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-violet-600"
            }`}
          >
            {liked ? "❤️" : "🤍"} Like
          </button>
          <span className="text-sm text-zinc-400">
            {likeCount} {likeCount === 1 ? "like" : "likes"} · {comments.length}{" "}
            {comments.length === 1 ? "comment" : "comments"}
          </span>
        </div>

        {/* Comment form */}
        <div className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <h3 className="mb-4 text-lg font-semibold text-zinc-200">
            Leave a Comment
          </h3>
          <form onSubmit={submitComment} className="space-y-4">
            <input
              type="text"
              placeholder="Your name"
              value={commentName}
              onChange={(e) => setCommentName(e.target.value)}
              maxLength={100}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
            <textarea
              placeholder="Write a comment..."
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              rows={3}
              maxLength={2000}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 resize-none"
            />
            {commentError && (
              <p className="text-sm text-red-400">{commentError}</p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-violet-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              {submitting ? "Posting..." : "Post Comment"}
            </button>
          </form>
        </div>

        {/* Comments list */}
        <div>
          <h3 className="mb-4 text-lg font-semibold text-zinc-200">
            Comments ({comments.length})
          </h3>
          {comments.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No comments yet. Be the first!
            </p>
          ) : (
            <div className="space-y-4">
              {comments.map((c) => (
                <div
                  key={c.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-sm font-semibold text-violet-400">
                      {c.username}
                    </span>
                    <span className="text-xs text-zinc-600">
                      {new Date(c.createdAt).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-300 whitespace-pre-wrap">
                    {c.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
