"use client";

import { useEffect } from "react";

export function useViewportHeight() {
  useEffect(() => {
    const root = document.documentElement;
    const viewport = window.visualViewport;
    let animationFrame: number | null = null;

    const updateHeight = () => {
      const height = viewport?.height ?? window.innerHeight;
      root.style.setProperty("--app-vh", `${Math.round(height)}px`);

      if (viewport && window.innerHeight - viewport.height > 120) {
        root.dataset.kb = "open";
      } else {
        delete root.dataset.kb;
      }
    };

    const scheduleUpdate = () => {
      if (animationFrame !== null) return;

      animationFrame = window.requestAnimationFrame(() => {
        animationFrame = null;
        updateHeight();
      });
    };

    const handleResize = () => scheduleUpdate();

    updateHeight();

    if (viewport) {
      viewport.addEventListener("resize", handleResize);
    } else {
      window.addEventListener("resize", handleResize);
    }

    return () => {
      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame);
      }
      if (viewport) {
        viewport.removeEventListener("resize", handleResize);
      } else {
        window.removeEventListener("resize", handleResize);
      }
      root.style.removeProperty("--app-vh");
      delete root.dataset.kb;
    };
  }, []);
}
