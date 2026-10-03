import NotificationPreferences from "@/components/notification-preferences";

export const metadata = { title: "Notification preferences", robots: { index: false, follow: false } };

export default function Page() {
  return <section className="wrap section">
    <p className="eyebrow">Your account</p>
    <h1>Stay updated.</h1>
    <NotificationPreferences />
  </section>;
}
