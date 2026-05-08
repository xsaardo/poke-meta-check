import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-20 py-6 border-t border-[#E0E0E0] text-center text-[#888888] text-sm space-y-2">
      <div className="flex justify-center gap-6">
        <Link href="/" className="text-[#CC0000] hover:underline">
          Search
        </Link>
        <Link href="/sets" className="text-[#CC0000] hover:underline">
          Card Sets
        </Link>
      </div>
      <div>
        Tournament data sourced from{" "}
        <a
          href="https://limitlesstcg.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#CC0000] hover:underline"
        >
          Limitless TCG
        </a>
        {" · "}
        Card data from{" "}
        <a
          href="https://pokemontcg.io"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#CC0000] hover:underline"
        >
          pokemontcg.io
        </a>
      </div>
    </footer>
  );
}
