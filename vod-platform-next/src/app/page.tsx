import Link from "next/link";
import { db } from "../db";
export const dynamic = "force-dynamic";
import { videos } from "../db/schema";
import { desc, eq, sql } from "drizzle-orm";

type VideoWithCounts = {
  id: number; title: string; playerUrl: string; hlsUrl: string;
  visible: number; createdAt: string; likeCount: number; commentCount: number;
};

const gradients = [
  "from-violet-600 to-indigo-600", "from-fuchsia-600 to-pink-600",
  "from-cyan-600 to-blue-600", "from-emerald-600 to-teal-600",
  "from-amber-600 to-orange-600", "from-rose-600 to-red-600",
  "from-sky-600 to-cyan-600", "from-purple-600 to-violet-600",
];

export default async function HomePage() {
  const rows = db.select({
    id: videos.id, title: videos.title, playerUrl: videos.playerUrl,
    hlsUrl: videos.hlsUrl, visible: videos.visible, createdAt: videos.createdAt,
    likeCount: sql<number>`(SELECT COUNT(*) FROM likes WHERE likes.video_id = ${videos.id})`,
    commentCount: sql<number>`(SELECT COUNT(*) FROM comments WHERE comments.video_id = ${videos.id})`,
  }).from(videos).where(eq(videos.visible, 1)).orderBy(desc(videos.createdAt)).all() as VideoWithCounts[];

  return (
    <main className="max-w-[1720px] mx-auto px-4 sm:px-6 py-6">
      {/* Category chips */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-none">
        {["All", "Meetings", "Courses", "Recordings", "Live", "Recent"].map((tag, i) => (
          <button key={tag} className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
            i === 0 ? "bg-white text-black" : "bg-white/[0.06] text-zinc-300 hover:bg-white/[0.12]"
          }`}>{tag}</button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 text-zinc-500">
          <div className="w-24 h-24 rounded-full bg-white/[0.04] flex items-center justify-center mb-6">
            <svg className="w-10 h-10 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-lg font-medium text-zinc-400">No videos yet</p>
          <p className="text-sm text-zinc-600 mt-1">Recordings will appear here automatically</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {rows.map((video, i) => (
            <Link key={video.id} href={`/watch/${video.id}`} className="group">
              {/* Thumbnail */}
              <div className={`relative aspect-video rounded-xl overflow-hidden mb-3 bg-gradient-to-br ${gradients[i % gradients.length]}`}>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-14 h-14 rounded-full bg-black/40 backdrop-blur-sm flex items-center justify-center group-hover:bg-black/60 transition-all group-hover:scale-110">
                    <svg className="w-6 h-6 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </div>
                </div>
                {/* Duration badge */}
                <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-xs font-medium bg-black/80 text-white">
                  Video
                </span>
              </div>

              {/* Info */}
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 shrink-0 flex items-center justify-center text-xs font-bold">
                  V
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-zinc-100 line-clamp-2 leading-snug group-hover:text-white transition-colors">
                    {video.title}
                  </h3>
                  <p className="text-xs text-zinc-500 mt-1">JitsiVOD</p>
                  <p className="text-xs text-zinc-500">
                    {video.likeCount > 0 && <span>{video.likeCount} likes</span>}
                    {video.likeCount > 0 && video.commentCount > 0 && <span> · </span>}
                    {video.commentCount > 0 && <span>{video.commentCount} comments</span>}
                    {(video.likeCount > 0 || video.commentCount > 0) && <span> · </span>}
                    {new Date(video.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
