// web/src/lib/active.ts
const KEY = "active_block_id";
export const ACTIVE_EVENT = "active-block-change";

export const getActiveBlock = () => {
  if (typeof window === "undefined") return null;
  const v = window.localStorage.getItem(KEY);
  return v ? Number(v) : null;
};

export const setActiveBlock = (id: number) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, String(id));
  window.dispatchEvent(new CustomEvent(ACTIVE_EVENT, { detail: { id } }));
};

export const clearActiveBlock = () => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
  window.dispatchEvent(new CustomEvent(ACTIVE_EVENT, { detail: { id: null } }));
};
