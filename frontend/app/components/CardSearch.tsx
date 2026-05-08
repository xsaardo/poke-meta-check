"use client";

import { useEffect, useRef, useState } from "react";
import { autocomplete, CardSuggestion } from "../lib/api";

interface Props {
  onSelect: (card: CardSuggestion) => void;
  isLoading: boolean;
  compact?: boolean;
  clearAfterSelect?: boolean;
  placeholder?: string;
}

export function CardSearch({ onSelect, isLoading, compact = false, clearAfterSelect = false, placeholder }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<CardSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    if (query.length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    debounce.current = setTimeout(async () => {
      const results = await autocomplete(query);
      setSuggestions(results);
      setOpen(results.length > 0);
      setActiveIdx(-1);
    }, 250);
    return () => {
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      selectCard(suggestions[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  function selectCard(card: CardSuggestion) {
    setQuery(clearAfterSelect ? "" : card.name);
    setOpen(false);
    setSuggestions([]);
    onSelect(card);
  }

  const inputClass = compact
    ? "w-full px-4 py-2 pr-10 rounded-lg bg-white border border-[#E0E0E0] text-[#111111] placeholder-[#AAAAAA] text-sm focus:outline-none focus:border-[#CC0000]/60 transition disabled:opacity-50"
    : "w-full px-5 py-4 pr-12 rounded-xl bg-white border border-[#E0E0E0] text-[#111111] placeholder-[#AAAAAA] text-lg focus:outline-none focus:border-[#CC0000] focus:ring-1 focus:ring-[#CC0000] transition disabled:opacity-50";

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder={placeholder ?? "Search a card name… (e.g. Charizard ex)"}
          disabled={isLoading}
          className={inputClass}
        />
        {isLoading ? (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="w-5 h-5 border-2 border-[#CC0000] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : query ? (
          <button
            onClick={() => { setQuery(""); setSuggestions([]); setOpen(false); }}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-[#AAAAAA] hover:text-[#111111] transition"
          >
            ✕
          </button>
        ) : (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#AAAAAA] text-xl">⚡</span>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 w-full mt-2 rounded-xl bg-white border border-[#E0E0E0] overflow-hidden shadow-xl shadow-black/5">
          {suggestions.map((card, idx) => (
            <li
              key={card.id}
              onMouseDown={() => selectCard(card)}
              onMouseEnter={() => setActiveIdx(idx)}
              className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition ${
                idx === activeIdx ? "bg-[#F5F5F5]" : "hover:bg-[#F9F9F9]"
              }`}
            >
              {card.image_url_small && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={card.image_url_small}
                  alt={card.name}
                  width={36}
                  height={52}
                  className="rounded object-cover flex-shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="text-[#111111] font-medium truncate">{card.name}</div>
                <div className="text-[#888888] text-sm truncate">
                  {card.supertype}{card.subtypes ? ` · ${card.subtypes}` : ""}
                  {card.set_code ? ` · ${card.set_code}${card.card_number ? ` #${card.card_number}` : ""}` : ""}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
