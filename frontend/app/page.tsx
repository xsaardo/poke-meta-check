"use client";

import Image from "next/image";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CardSearch } from "./components/CardSearch";
import { Footer } from "./components/Footer";
import { MetaBadge } from "./components/MetaBadge";
import { TournamentTable } from "./components/TournamentTable";
import { CardPrices, CardSuggestion, SearchResult, autocomplete, getCard, getCardPrices, searchCard } from "./lib/api";

const MONTH_OPTIONS = [1, 2, 3] as const;

function HomePageContent() {
  const searchParams = useSearchParams();
  const [selectedCard, setSelectedCard] = useState<CardSuggestion | null>(null);
  const [months, setMonths] = useState(3);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [prices, setPrices] = useState<CardPrices | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCardSelect(card: CardSuggestion) {
    setSelectedCard(card);
    setError(null);
    setIsLoading(true);
    setPrices(null);
    try {
      const [data, priceData] = await Promise.all([
        searchCard(card.name, months, card.set_code, card.card_number),
        card.set_code && card.card_number
          ? getCardPrices(card.set_code, card.card_number)
          : Promise.resolve(null),
      ]);
      if (!data) throw new Error("Search failed");
      setResult(data);
      setPrices(priceData);
    } catch {
      setError("Failed to fetch results. Is the backend running?");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function refetch(newMonths = months) {
    if (!selectedCard) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await searchCard(selectedCard.name, newMonths, selectedCard.set_code, selectedCard.card_number);
      if (!data) throw new Error("Search failed");
      setResult(data);
    } catch {
      setError("Failed to fetch results.");
    } finally {
      setIsLoading(false);
    }
  }

  // Auto-search when navigated from the sets page with ?card=<name>&set_code=<code>&card_number=<num>
  useEffect(() => {
    const cardName = searchParams.get("card");
    if (!cardName) return;
    const setCode = searchParams.get("set_code");
    const cardNumber = searchParams.get("card_number");

    if (setCode && cardNumber) {
      // Fetch the exact printing directly — don't rely on autocomplete's 10-result limit
      getCard(setCode, cardNumber).then((card) => {
        if (card) handleCardSelect(card);
        else {
          // Card not in local DB; fall back to name-only autocomplete
          autocomplete(cardName).then((suggestions) => {
            const match = suggestions.find((s) => s.name.toLowerCase() === cardName.toLowerCase()) ?? suggestions[0];
            if (match) handleCardSelect(match);
          });
        }
      });
    } else {
      autocomplete(cardName).then((suggestions) => {
        const match = suggestions.find((s) => s.name.toLowerCase() === cardName.toLowerCase()) ?? suggestions[0];
        if (match) handleCardSelect(match);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <main className="min-h-screen px-4 py-12 md:py-20">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold text-[#111111] mb-3 tracking-tight">
          Pokemon TCG Meta Check
        </h1>
        <p className="text-[#888888] text-lg max-w-xl mx-auto">
          Search any card to see if it has Standard format tournament relevance in the last{" "}
          {months} months.
        </p>
        <Link href="/sets" className="inline-block mt-4 text-sm text-[#CC0000] hover:underline">
          Browse by set →
        </Link>
      </div>

      {/* Search */}
      <CardSearch onSelect={handleCardSelect} isLoading={isLoading} />

      {/* Filters */}
      <div className="flex flex-wrap justify-center gap-3 mt-6">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2">
          <span className="text-[#888888] text-sm">Last</span>
          {MONTH_OPTIONS.map((m) => (
            <button
              key={m}
              onClick={() => {
                setMonths(m);
                refetch(m);
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                months === m
                  ? "bg-[#CC0000] text-white"
                  : "text-[#888888] hover:text-[#111111]"
              }`}
            >
              {m}mo
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="max-w-2xl mx-auto mt-8 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm text-center">
          {error}
        </div>
      )}

      {/* Results */}
      {result && selectedCard && (
        <div className="max-w-5xl mx-auto mt-10 space-y-6">
          {/* Card identity */}
          <div className="flex items-start gap-5 p-5 rounded-xl bg-white border border-gray-200">
            {selectedCard.image_url_small && (
              <Image
                src={selectedCard.image_url_small}
                alt={selectedCard.name}
                width={60}
                height={88}
                className="rounded-md flex-shrink-0 shadow-md"
                unoptimized
              />
            )}
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-[#111111]">{result.card_name}</h2>
              <div className="text-[#888888] text-sm">
                {selectedCard.supertype}
                {selectedCard.subtypes ? ` · ${selectedCard.subtypes}` : ""}
              </div>
              <MetaBadge relevant={result.meta_relevant} count={result.total_appearances} />
              {prices && (prices.tcgplayer || prices.cardmarket) && (
                <div className="flex flex-wrap gap-3 pt-1">
                  {prices.tcgplayer && (
                    <span className="text-xs text-[#888888]">
                      TCGPlayer{" "}
                      <span className="text-[#111111] font-medium">${prices.tcgplayer}</span>
                    </span>
                  )}
                  {prices.cardmarket && (
                    <span className="text-xs text-[#888888]">
                      Cardmarket{" "}
                      <span className="text-[#111111] font-medium">€{prices.cardmarket}</span>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Table */}
          {result.results.length > 0 ? (
            <TournamentTable results={result.results} />
          ) : (
            <div className="text-center py-16 text-[#888888]">
              <div className="text-5xl mb-4">🃏</div>
              <p className="text-lg">No confirmed tournament decklists found for this card.</p>
              <p className="text-sm mt-2 max-w-md mx-auto">
                This card may be played in tournaments where decklists weren&apos;t published,
                or it may genuinely not be in the current meta.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !isLoading && !error && (
        <div className="text-center mt-20 text-[#888888]">
          <div className="text-6xl mb-4">⚡</div>
          <p className="text-lg">Type a card name to check its meta relevance</p>
          <p className="text-sm mt-1">Tournament data sourced from Limitless TCG</p>
        </div>
      )}

      <Footer />
    </main>
  );
}

export default function HomePage() {
  return (
    <Suspense>
      <HomePageContent />
    </Suspense>
  );
}
