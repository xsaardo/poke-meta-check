"use client";

import { useState } from "react";
import { DeckAppearance } from "../lib/api";

interface Props {
  results: DeckAppearance[];
}

type SortKey = "date" | "placement" | "deck" | "copies";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 20;

function placementBadge(placement: number | null) {
  if (!placement) return null;
  let cls = "bg-gray-100 text-gray-500 border-gray-200";
  let label = `${placement}`;

  if (placement === 1) {
    cls = "bg-yellow-50 text-yellow-700 border-yellow-200";
    label = "1st";
  } else if (placement === 2) {
    cls = "bg-slate-100 text-slate-600 border-slate-200";
    label = "2nd";
  } else if (placement <= 4) {
    cls = "bg-orange-50 text-orange-700 border-orange-200";
    label = "Top 4";
  } else if (placement <= 8) {
    cls = "bg-blue-50 text-blue-700 border-blue-200";
    label = "Top 8";
  } else if (placement <= 16) {
    cls = "bg-indigo-50 text-indigo-700 border-indigo-200";
    label = "Top 16";
  } else if (placement <= 32) {
    cls = "bg-gray-100 text-gray-500 border-gray-200";
    label = "Top 32";
  }

  return (
    <span className={`inline-block px-2 py-0.5 rounded-full border text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function sortRows(rows: DeckAppearance[], key: SortKey, dir: SortDir): DeckAppearance[] {
  const factor = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    switch (key) {
      case "date":
        return factor * a.tournament_date.localeCompare(b.tournament_date);
      case "placement":
        return factor * ((a.placement ?? 9999) - (b.placement ?? 9999));
      case "deck":
        return factor * (a.deck_archetype ?? "").localeCompare(b.deck_archetype ?? "");
      case "copies":
        return factor * (a.card_quantity - b.card_quantity);
      default:
        return 0;
    }
  });
}

interface HeaderProps {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
}

function SortableHeader({ label, sortKey, current, dir, onSort }: HeaderProps) {
  const active = current === sortKey;
  return (
    <th
      className="px-4 py-3 font-medium cursor-pointer select-none whitespace-nowrap group"
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <span className={`text-xs transition ${active ? "text-[#CC0000]" : "text-gray-300 group-hover:text-gray-400"}`}>
          {active ? (dir === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </span>
    </th>
  );
}

function MobileCard({ row }: { row: DeckAppearance }) {
  const isDeckLink = !!row.deck_url;
  return (
    <div className="p-4 border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-2 mb-2">
        <a
          href={row.tournament_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#CC0000] hover:underline font-medium text-sm leading-snug"
        >
          {row.tournament_name}
        </a>
        <span className="text-[#888888] text-xs whitespace-nowrap shrink-0">
          {new Date(row.tournament_date).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        {placementBadge(row.placement)}
        <span className="font-mono font-bold text-[#111111] text-xs">×{row.card_quantity}</span>
      </div>
      <div className="text-xs text-[#888888]">
        Deck:{" "}
        {isDeckLink ? (
          <a
            href={row.deck_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#111111] hover:text-[#CC0000] transition"
          >
            {row.deck_archetype ?? "Unknown"} <span className="text-[#888888]">↗</span>
          </a>
        ) : (
          <span className="text-[#111111]">{row.deck_archetype ?? "Unknown"}</span>
        )}
        {row.player_name && (
          <span className="ml-2 text-[#888888]">· {row.player_name}</span>
        )}
      </div>
    </div>
  );
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm">
      <span className="text-[#888888]">
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page === 1}
          className="px-3 py-1 rounded text-[#888888] hover:text-[#111111] disabled:opacity-30 disabled:cursor-not-allowed transition"
        >
          ← Prev
        </button>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page === totalPages}
          className="px-3 py-1 rounded text-[#888888] hover:text-[#111111] disabled:opacity-30 disabled:cursor-not-allowed transition"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

export function TournamentTable({ results }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "copies" ? "desc" : key === "placement" ? "asc" : "desc");
    }
    setPage(1);
  }

  const sorted = sortRows(results, sortKey, sortDir);
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paginated = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="rounded-xl border border-gray-200 bg-white">
      {/* Mobile */}
      <div className="md:hidden">
        {paginated.map((row, i) => (
          <MobileCard key={i} row={row} />
        ))}
        <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      </div>

      {/* Desktop */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-[#888888] text-left">
              <th className="px-4 py-3 font-medium">Tournament</th>
              <SortableHeader label="Date" sortKey="date" current={sortKey} dir={sortDir} onSort={handleSort} />
              <SortableHeader label="Placement" sortKey="placement" current={sortKey} dir={sortDir} onSort={handleSort} />
              <SortableHeader label="Deck" sortKey="deck" current={sortKey} dir={sortDir} onSort={handleSort} />
              <SortableHeader label="Copies" sortKey="copies" current={sortKey} dir={sortDir} onSort={handleSort} />
            </tr>
          </thead>
          <tbody>
            {paginated.map((row, i) => (
              <tr
                key={i}
                className="border-b border-gray-100 hover:bg-gray-50 transition"
              >
                <td className="px-4 py-3">
                  <a
                    href={row.tournament_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#CC0000] hover:underline font-medium"
                  >
                    {row.tournament_name}
                  </a>
                </td>
                <td className="px-4 py-3 text-[#888888] whitespace-nowrap">
                  {new Date(row.tournament_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </td>
                <td className="px-4 py-3">{placementBadge(row.placement)}</td>
                <td className="px-4 py-3">
                  {row.deck_url ? (
                    <a
                      href={row.deck_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#111111] hover:text-[#CC0000] transition flex items-center gap-1"
                    >
                      {row.deck_archetype ?? "Unknown"}
                      <span className="text-[#888888] text-xs">↗</span>
                    </a>
                  ) : (
                    <span className="text-[#111111]">{row.deck_archetype ?? "Unknown"}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono font-bold text-[#111111]">×{row.card_quantity}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      </div>
    </div>
  );
}
