import { useEffect, useState } from "react";
import { api, Cliente } from "./api";

// Cartera de demo compartida entre pantallas (se pide una sola vez).
let cache: Promise<Cliente[]> | null = null;

export function useCartera() {
  const [datos, setDatos] = useState<Cliente[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    cache ??= api.cartera(30, 7);
    cache.then(setDatos).catch((e: Error) => {
      cache = null;
      setError(e.message);
    });
  }, []);
  return { datos, error };
}
