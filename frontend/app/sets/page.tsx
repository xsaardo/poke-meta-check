"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Footer } from "../components/Footer";
import {
  getSets,
  getSetCards,
  type SetCard,
  type SetSummary,
} from "../lib/api";

const MONTH_OPTIONS = [1, 2, 3] as const;

// ── Set List View ─────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

function SetListView({ months }: { months: number }) {
  const router = useRouter();
  const [sets, setSets] = useState<SetSummary[] | null>(null);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSets(months)
      .then((data) => {
        if (!data) setError("Failed to load sets.");
        else setSets(data.sets);
      })
      .finally(() => setLoading(false));
  }, [months]);

  const filtered = sets
    ? sets.filter((s) => s.name.toLowerCase().includes(filter.toLowerCase()))
    : [];

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div>
      <input
        type="text"
        value={filter}
        onChange={(e) => { setFilter(e.target.value); setPage(1); }}
        placeholder="Search sets…"
        className="w-full mb-6 px-4 py-2 rounded-lg bg-white border border-gray-200 text-[#111111] placeholder-[#AAAAAA] focus:outline-none focus:border-[#CC0000]"
      />

      {loading && <p className="text-center text-[#888888] py-12">Loading sets…</p>}
      {error && <p className="text-center text-red-600 py-12">{error}</p>}
      {!loading && !error && filtered.length === 0 && (
        <p className="text-center text-[#888888] py-12">No sets found.</p>
      )}

      {!loading && !error && filtered.length > 0 && (
        <>
          <div className="grid gap-3">
            {paginated.map((s) => {
              const pct =
                s.card_count > 0
                  ? Math.round((s.meta_relevant_count / s.card_count) * 100)
                  : 0;
              return (
                <button
                  key={s.name}
                  onClick={() => {
                    const params = new URLSearchParams({ set: s.name, months: String(months) });
                    router.push(`/sets?${params}`);
                  }}
                  className="w-full text-left px-5 py-4 rounded-xl bg-white border border-gray-200 hover:border-[#CC0000] transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 min-w-0">
                      {s.logo_url && (
                        <Image
                          src={s.logo_url}
                          alt={s.name}
                          width={80}
                          height={32}
                          className="object-contain shrink-0"
                          unoptimized
                        />
                      )}
                      <span className="text-[#111111] font-medium truncate">{s.name}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 text-sm">
                      <span className="text-[#888888]">{s.card_count} cards</span>
                      {s.meta_relevant_count > 0 ? (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold">
                          {s.meta_relevant_count} meta ({pct}%)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-[#888888] text-xs">
                          0 meta
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 text-[#888888] hover:border-[#CC0000] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Prev
              </button>
              <span className="text-sm text-[#888888]">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 text-[#888888] hover:border-[#CC0000] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Set Detail View ───────────────────────────────────────────────────────────

function SetDetailView({ setName, months }: { setName: string; months: number }) {
  const router = useRouter();
  const [cards, setCards] = useState<SetCard[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metaOnly, setMetaOnly] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSetCards(setName, months)
      .then((data) => {
        if (!data) setError("Failed to load set cards.");
        else setCards(data.cards);
      })
      .finally(() => setLoading(false));
  }, [setName, months]);

  const displayed = cards
    ? metaOnly
      ? cards.filter((c) => c.tournament_count > 0)
      : cards
    : [];

  const metaCount = cards ? cards.filter((c) => c.tournament_count > 0).length : 0;

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => {
            const params = new URLSearchParams({ months: String(months) });
            router.push(`/sets?${params}`);
          }}
          className="text-[#CC0000] hover:underline text-sm"
        >
          ← All Sets
        </button>
      </div>
      <h2 className="text-2xl font-bold text-[#111111] mb-1">{setName}</h2>
      {!loading && cards && (
        <p className="text-[#888888] text-sm mb-5">
          {cards.length} cards · {metaCount} meta-relevant in last {months} month{months !== 1 ? "s" : ""}
        </p>
      )}

      <div className="flex gap-2 mb-6">
        {(["All cards", "Meta relevant only"] as const).map((label, i) => {
          const active = i === 0 ? !metaOnly : metaOnly;
          return (
            <button
              key={label}
              onClick={() => setMetaOnly(i === 1)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                active
                  ? "bg-[#CC0000] text-white"
                  : "bg-white text-[#888888] border border-gray-200 hover:border-[#CC0000]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {loading && <p className="text-center text-[#888888] py-12">Loading cards…</p>}
      {error && <p className="text-center text-red-600 py-12">{error}</p>}
      {!loading && !error && displayed.length === 0 && (
        <p className="text-center text-[#888888] py-12">
          {metaOnly ? "No meta-relevant cards in this set for the selected period." : "No cards found."}
        </p>
      )}

      {!loading && !error && displayed.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {displayed.map((card) => (
            <Link
              key={card.id}
              href={(() => {
                const [setCode, ...rest] = card.id.split("-");
                const cardNumber = rest.join("-");
                const p = new URLSearchParams({ card: card.name, set_code: setCode, card_number: cardNumber });
                return `/?${p}`;
              })()}
              className={`group flex flex-col rounded-xl overflow-hidden border transition-colors ${
                card.tournament_count > 0
                  ? "border-gray-200 hover:border-[#CC0000]"
                  : "border-gray-100 opacity-50 hover:opacity-75 hover:border-gray-200"
              } bg-white`}
            >
              <div className="relative aspect-[421/614] w-full bg-gray-50">
                {card.image_path && (
                  <Image
                    src={card.image_path}
                    alt={card.name}
                    fill
                    sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 20vw"
                    className="object-cover"
                    unoptimized
                  />
                )}
              </div>
              <div className="p-2 flex-1 flex flex-col gap-1">
                <p className="text-[#111111] text-xs font-medium leading-tight line-clamp-2 group-hover:text-[#CC0000]">
                  {card.name}
                </p>
                <p className="text-[#888888] text-xs truncate">{card.supertype}</p>
                {card.tournament_count > 0 ? (
                  <span className="mt-auto inline-block px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold">
                    {card.tournament_count} tournament{card.tournament_count !== 1 ? "s" : ""}
                  </span>
                ) : (
                  <span className="mt-auto text-[#888888] text-xs">Not meta</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page Shell ────────────────────────────────────────────────────────────────

function SetsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const setName = searchParams.get("set");
  const monthsParam = parseInt(searchParams.get("months") ?? "3", 10);
  const months = MONTH_OPTIONS.includes(monthsParam as (typeof MONTH_OPTIONS)[number])
    ? monthsParam
    : 3;

  function setMonths(m: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("months", String(m));
    router.push(`/sets?${params}`);
  }

  return (
    <main className="min-h-screen bg-[#FAFAFA] text-[#111111]">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-2">
          <div>
            <Link href="/" className="text-[#CC0000] hover:underline text-sm">
              ← Search
            </Link>
            <h1 className="text-3xl font-bold text-[#111111] mt-1">Card Sets</h1>
            <p className="text-[#888888] text-sm mt-1">
              Browse meta-relevant cards by set
            </p>
          </div>
          <div className="flex gap-1">
            {MONTH_OPTIONS.map((m) => (
              <button
                key={m}
                onClick={() => setMonths(m)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  months === m
                    ? "bg-[#CC0000] text-white"
                    : "bg-white text-[#888888] border border-gray-200 hover:border-[#CC0000]"
                }`}
              >
                {m}mo
              </button>
            ))}
          </div>
        </div>

        <div className="border-t border-gray-200 mt-6 pt-6">
          {setName ? (
            <SetDetailView setName={setName} months={months} />
          ) : (
            <SetListView months={months} />
          )}
        </div>
      </div>
      <Footer />
    </main>
  );
}

export default function SetsPage() {
  return (
    <Suspense>
      <SetsPageContent />
    </Suspense>
  );
}
