import { useEffect, useRef, useState } from "react";

/**
 * Returns a ref + a boolean. Attach the ref to an element; the boolean
 * flips to true the first time the element scrolls into view.
 *
 * Used by the landing page to delay animations on below-the-fold sections
 * until the visitor actually scrolls down to them.
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>(
  rootMargin: string = "-80px",
) {
  const ref = useRef<T | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect(); // animate once, then stop watching
        }
      },
      { rootMargin, threshold: 0 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [rootMargin]);

  return { ref, isVisible };
}
