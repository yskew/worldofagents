import { useCallback, useEffect, useRef, useState } from 'react';

const SECTION_COUNT = 8;

export function useScrollScene() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<(HTMLElement | null)[]>(Array(SECTION_COUNT).fill(null));
  const [activeSection, setActiveSection] = useState(0);
  const [sectionProgress, setSectionProgress] = useState<Map<number, number>>(new Map());

  const setSectionRef = useCallback((index: number) => (el: HTMLElement | null) => {
    sectionRefs.current[index] = el;
  }, []);

  const scrollToSection = useCallback((index: number) => {
    sectionRefs.current[index]?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const vh = window.innerHeight;
      const newProgress = new Map<number, number>();
      let closestIndex = 0;
      let closestDist = Infinity;

      for (let i = 0; i < SECTION_COUNT; i++) {
        const el = sectionRefs.current[i];
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        const progress = Math.max(0, Math.min(1, 1 - rect.top / vh));
        newProgress.set(i, progress);

        const dist = Math.abs(rect.top);
        if (dist < closestDist) {
          closestDist = dist;
          closestIndex = i;
        }
      }

      setSectionProgress(newProgress);
      setActiveSection(closestIndex);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault();
        const next = Math.min(SECTION_COUNT - 1, activeSection + 1);
        sectionRefs.current[next]?.scrollIntoView({ behavior: 'smooth' });
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault();
        const prev = Math.max(0, activeSection - 1);
        sectionRefs.current[prev]?.scrollIntoView({ behavior: 'smooth' });
      }
    };

    window.addEventListener('keydown', handleKey);

    return () => {
      container.removeEventListener('scroll', handleScroll);
      window.removeEventListener('keydown', handleKey);
    };
  }, [activeSection]);

  return { activeSection, sectionProgress, scrollToSection, containerRef, setSectionRef };
}
