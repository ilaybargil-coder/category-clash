"use client";

import { useEffect } from "react";

export function useViewportHeight() {
  useEffect(() => {
    const root = document.documentElement;
    const viewport = window.visualViewport;
    let animationFrame: number | null = null;
    let shouldResetScroll = false;

    const updateHeight = () => {
      const height = viewport?.height ?? window.innerHeight;
      root.style.setProperty("--app-vh", `${Math.round(height)}px`);

      if (viewport && window.innerHeight - viewport.height > 120) {
        root.dataset.kb = "open";
      } else {
        delete root.dataset.kb;
      }
    };

    const scheduleUpdate = (resetScroll = false) => {
      shouldResetScroll ||= resetScroll;
      if (animationFrame !== null) return;

      animationFrame = window.requestAnimationFrame(() => {
        animationFrame = null;
        if (shouldResetScroll) window.scrollTo(0, 0);
        shouldResetScroll = false;
        updateHeight();
      });
    };

    const handleResize = () => scheduleUpdate();
    const handleScroll = () => scheduleUpdate(true);

    updateHeight();

    if (viewport) {
      viewport.addEventListener("resize", handleResize);
      viewport.addEventListener("scroll", handleScroll);
    } else {
      window.addEventListener("resize", handleResize);
    }

    return () => {
      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame);
      }
      if (viewport) {
        viewport.removeEventListener("resize", handleResize);
        viewport.removeEventListener("scroll", handleScroll);
      } else {
        window.removeEventListener("resize", handleResize);
      }
      root.style.removeProperty("--app-vh");
      delete root.dataset.kb;
    };
  }, []);
}
