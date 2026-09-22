type Name = "search" | "heart" | "bag" | "leaf" | "truck" | "sparkle" | "arrow";
const paths: Record<Name, string> = {
  search: "M21 21l-5-5M19 10.5a8.5 8.5 0 1 1-17 0 8.5 8.5 0 0 1 17 0Z",
  heart:
    "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z",
  bag: "M5 7h14l1 14H4L5 7Zm3 0V6a4 4 0 0 1 8 0v1",
  leaf: "M20 3C9 2 3 6 4 13c1 7 9 8 13 2 3-4 3-8 3-12ZM4 21 15 9",
  truck:
    "M1 4h13v13H1V4Zm13 5h5l4 5v3h-9M7 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm14 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z",
  sparkle: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z",
  arrow: "M4 12h16m-6-6 6 6-6 6",
};
export default function Icon({ name }: { name: Name }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
