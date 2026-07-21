"use client";

import { useEffect } from "react";

export function useViewportHeight() {
  useEffect(() => {
    const root = document.documentElement;
    const viewport = window.visualViewport;
    let baseline = viewport?.height ?? window.innerHeight;
    let animationFrame: number | null = null;

    const updateViewport = () => {
      const height = viewport?.height ?? window.innerHeight;
      const offsetTop = viewport?.offsetTop ?? 0;

      if (viewport && viewport.height > baseline) {
        baseline = viewport.height;
      }

      root.style.setProperty("--app-vh", `${height}px`);
      root.style.setProperty("--app-top", `${offsetTop}px`);

      if (viewport && (baseline - viewport.height > 120 || viewport.offsetTop > 0)) {
        root.dataset.kb = "open";
      } else {
        delete root.dataset.kb;
      }
    };

    const scheduleUpdate = () => {
      if (animationFrame !== null) return;

      animationFrame = window.requestAnimationFrame(() => {
        animationFrame = null;
        updateViewport();
      });
    };

    const handleViewportChange = () => scheduleUpdate();

    updateViewport();

    if (viewport) {
      // iOS can pan the visual viewport when its keyboard opens. Height alone
      // is insufficient: fixed game UI must also follow this changing offset.
      viewport.addEventListener("resize", handleViewportChange);
      viewport.addEventListener("scroll", handleViewportChange);
    } else {
      window.addEventListener("resize", handleViewportChange);
    }

    return () => {
      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame);
      }
      if (viewport) {
        viewport.removeEventListener("resize", handleViewportChange);
        viewport.removeEventListener("scroll", handleViewportChange);
      } else {
        window.removeEventListener("resize", handleViewportChange);
      }
      root.style.removeProperty("--app-vh");
      root.style.removeProperty("--app-top");
      delete root.dataset.kb;
    };
  }, []);
}
