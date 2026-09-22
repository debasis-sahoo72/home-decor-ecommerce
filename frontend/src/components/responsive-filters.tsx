"use client";
import { useSyncExternalStore } from "react";
function subscribe(callback: () => void) {
  const media = window.matchMedia("(max-width: 768px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
export default function ResponsiveFilters({
  children,
}: {
  children: React.ReactNode;
}) {
  const mobile = useSyncExternalStore(
    subscribe,
    () => window.matchMedia("(max-width: 768px)").matches,
    () => false,
  );
  return (
    <details
      key={mobile ? "mobile" : "desktop"}
      className="filter-panel"
      open={!mobile}
    >
      <summary>Filter & sort</summary>
      {children}
    </details>
  );
}
