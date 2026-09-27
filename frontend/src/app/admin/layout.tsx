import AdminShell from "@/components/admin-shell";
import "@/app/operations.css";
export const metadata = {
  title: "Store management",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
