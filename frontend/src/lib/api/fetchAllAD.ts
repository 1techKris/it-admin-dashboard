import api from "./client";

export async function fetchAllAD(route: string) {
  let page = 1;
  const all: any[] = [];

  while (true) {
    const res = await api.get(`${route}?page=${page}`);
    const items = res.data?.items ?? [];

    all.push(...items);

    if (items.length < 50) break; // no more pages
    page++;
  }

  return all;
}