// Reserved references keep local demo media portable; real media uses Cloudinary.
export function imageSource(url: string) {
  const prefix = "https://local-preview.invalid/demo/";
  return url.startsWith(prefix) ? `/demo/${url.slice(prefix.length)}` : url;
}
export function productName(name: string) {
  return name.replace(/^\[DEMO\]\s*/, "");
}
export function isDemo(name: string) {
  return name.startsWith("[DEMO]");
}
