"use client";

import { useEffect } from "react";
import App from "./App";

function registerServiceWorker() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => null);
  });
}

export default function ClientApp() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") registerServiceWorker();
  }, []);

  return <App />;
}
