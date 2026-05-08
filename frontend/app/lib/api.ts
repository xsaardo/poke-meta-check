const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CardSuggestion {
  id: string;           // "OBF-125" (string, not number)
  name: string;
  supertype: string;    // "Pokémon", "Trainer", "Energy"
  subtypes?: string | null;
  set_code?: string | null;
  card_number?: string | null;
  image_url_small: string;
}

export interface DeckAppearance {
  tournament_name: string;
  tournament_date: string;
  tournament_url: string;
  placement: number | null;
  player_name: string | null;
  deck_archetype: string | null;
  deck_url: string;
  card_supertype: string;
  card_quantity: number;
  format: string | null;
}

export interface SearchResult {
  card_name: string;
  meta_relevant: boolean;
  total_appearances: number;
  results: DeckAppearance[];
}

export interface CardPrices {
  tcgplayer: string | null;
  cardmarket: string | null;
}

export interface SetSummary {
  name: string;
  card_count: number;
  meta_relevant_count: number;
  logo_url: string | null;
}

export interface SetsResponse {
  sets: SetSummary[];
  months: number;
}

export interface SetCard {
  id: string;
  name: string;
  supertype: string;
  subtypes: string | null;
  image_path: string | null;
  deck_count: number;
  tournament_count: number;
}

export interface SetCardsResponse {
  set_name: string;
  months: number;
  cards: SetCard[];
}

export async function getCard(
  setCode: string,
  cardNumber: string,
): Promise<CardSuggestion | null> {
  const res = await fetch(`${API_URL}/api/cards/${encodeURIComponent(setCode)}/${encodeURIComponent(cardNumber)}`);
  if (!res.ok) return null;
  return res.json();
}

export async function autocomplete(q: string): Promise<CardSuggestion[]> {
  if (q.length < 2) return [];
  const res = await fetch(`${API_URL}/api/autocomplete?q=${encodeURIComponent(q)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function searchCard(
  cardName: string,
  months = 3,
  setCode?: string | null,
  cardNumber?: string | null,
): Promise<SearchResult | null> {
  const params = new URLSearchParams({ card: cardName, months: String(months) });
  if (setCode) params.set("set_code", setCode);
  if (cardNumber) params.set("card_number", cardNumber);
  const res = await fetch(`${API_URL}/api/search?${params}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getCardPrices(
  setCode: string,
  cardNumber: string
): Promise<CardPrices | null> {
  if (!setCode || !cardNumber) return null;
  const res = await fetch(`${API_URL}/api/prices/${encodeURIComponent(setCode)}/${encodeURIComponent(cardNumber)}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getSets(months = 3): Promise<SetsResponse | null> {
  const res = await fetch(`${API_URL}/api/sets?months=${months}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getSetCards(
  setName: string,
  months = 3
): Promise<SetCardsResponse | null> {
  const res = await fetch(
    `${API_URL}/api/sets/${encodeURIComponent(setName)}/cards?months=${months}`
  );
  if (!res.ok) return null;
  return res.json();
}
