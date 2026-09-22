import SignIn from "@/components/sign-in";
export const metadata = {
  title: "Your account",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section">
      <SignIn />
    </section>
  );
}
