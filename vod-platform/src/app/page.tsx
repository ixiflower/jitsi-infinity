import Link from "next/link";
import { db } from "../db";
import { videos } from "../db/schema";
import { desc, eq, sql } from "drizzle-orm";

type VideoWithCounts = {
  id: number;
  title: string;
  playerUrl: string;
  hlsUrl: string;
  visible: number;
  createdAt: string;
  likeCount: number;
  commentCount: number;
};

export default async function HomePage() {
  const rows = db
    .select({
      id: videos.id,
      title: videos.title,
      playerUrl: videos.playerUrl,
      hlsUrl: videos.hlsUrl,
      visible: videos.visible,
      createdAt: videos.createdAt,
      likeCount: sql<number>`(SELECT COUNT(*) FROM likes WHERE likes.video_id = ${videos.id})`,
      commentCount: sql<number>`(SELECT COUNT(*) FROM comments WHERE comments.video_id = ${videos.id})`,
    })
    .from(videos)
    .where(eq(videos.visible, 1))
    .orderBy(desc(videos.createdAt))
    .all() as VideoWithCounts[];

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🎬</span>
            <h1 className="text-xl font-bold tracking-tight text-violet-400">
              VOD Platform
            </h1>
          </Link>
          <Link
            href="/admin/login"
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:border-violet-500 hover:text-violet-400"
          >
            Admin
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-6 py-10">
        {rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-zinc-500">
            <span className="text-6xl mb-4">📼</span>
            <p className="text-lg">No videos available yet.</p>
            <p className="text-sm mt-2">Check back later for new content.</p>
          </div>
        ) : (
          <>
            <h2 className="mb-8 text-2xl font-semibold text-zinc-200">
              Available Videos
            </h2>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {rows.map((video) => (
                <Link
                  key={video.id}
                  href={`/watch/${video.id}`}
                  className="group rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-violet-700 hover:bg-zinc-900/80"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <h3 className="text-lg font-medium text-zinc-100 group-hover:text-violet-300 transition-colors line-clamp-2">
                      {video.title}
                    </h3>
                    <span className="mt-0.5 shrink-0 text-2xl">▶️</span>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-zinc-500">
                    <span className="flex items-center gap-1">
                      👍 {video.likeCount}
                    </span>
                    <span className="flex items-center gap-1">
                      💬 {video.commentCount}
                    </span>
                    <span className="ml-auto">
                      {new Date(video.createdAt).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
