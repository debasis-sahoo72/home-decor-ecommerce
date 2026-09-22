import AddressBook from "@/components/address-book";
export const metadata = {
  title: "Your addresses",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section">
      <p className="eyebrow">Your account · The places you call home</p>
      <h1>Your addresses</h1>
      <AddressBook />
    </section>
  );
}
