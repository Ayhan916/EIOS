"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/**
 * Top loading bar that appears between click and route completion.
 * Uses a document-level click listener to catch <Link> clicks early,
 * then hides when the pathname changes (navigation done).
 */
export function NavigationProgress() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);
  const [width, setWidth] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevPath = useRef(pathname);

  // Start the bar as soon as any <a> inside the app is clicked
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const target = (e.target as HTMLElement).closest("a[href]");
      if (!target) return;
      const href = (target as HTMLAnchorElement).getAttribute("href");
      if (!href || href.startsWith("http") || href.startsWith("#") || href === pathname) return;
      // Internal link — start progress bar
      setLoading(true);
      setWidth(15);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [pathname]);

  // Increment the bar while loading
  useEffect(() => {
    if (!loading) return;
    timerRef.current = setInterval(() => {
      setWidth((w) => {
        if (w >= 85) return 85; // stop short of 100 until navigation done
        return w + Math.random() * 8;
      });
    }, 200);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading]);

  // Complete the bar when pathname changes
  useEffect(() => {
    if (pathname !== prevPath.current) {
      prevPath.current = pathname;
      if (loading) {
        setWidth(100);
        if (timerRef.current) clearInterval(timerRef.current);
        const t = setTimeout(() => {
          setLoading(false);
          setWidth(0);
        }, 300);
        return () => clearTimeout(t);
      }
    }
  }, [pathname, loading]);

  if (!loading && width === 0) return null;

  return (
    <div
      className="fixed top-0 left-0 z-[9999] h-[2.5px] bg-blue-500 transition-all duration-200 ease-out shadow-[0_0_8px_rgba(59,130,246,0.6)]"
      style={{
        width: `${width}%`,
        opacity: loading ? 1 : 0,
        transition: width === 100 ? "width 150ms ease-out, opacity 200ms ease 200ms" : "width 200ms ease-out",
      }}
    />
  );
}
