import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "VOD Platform",
  description: "Watch recorded sessions anytime",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0f0f0f] text-white antialiased">
        {/* Top Navbar */}
        <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-[#0f0f0f]/95 backdrop-blur-sm border-b border-white/[0.06]">
          <div className="flex items-center justify-between h-full px-4 max-w-[1720px] mx-auto">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </div>
              <span className="text-lg font-semibold tracking-tight hidden sm:block">
                Jitsi<span className="text-violet-400">VOD</span>
              </span>
            </Link>

            <div className="flex items-center gap-3">
              <Link
                href="/admin/login"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="hidden sm:inline">Admin</span>
              </Link>
            </div>
          </div>
        </header>

        {/* Main content — offset for fixed header */}
        <div className="pt-14">
          {children}
        </div>
      </body>
    </html>
  );
}
