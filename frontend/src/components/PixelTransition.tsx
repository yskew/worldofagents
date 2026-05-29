import { useEffect, useRef, useState } from 'react';

interface Props {
  active: boolean;
  onComplete?: () => void;
  children: React.ReactNode;
}

export default function PixelTransition({ active, onComplete, children }: Props) {
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!active) { setDone(false); return; }

    const canvas = overlayRef.current!;
    const w = window.innerWidth;
    const h = window.innerHeight;
    const dpr = 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    const ctx = canvas.getContext('2d')!;

    // fill with the paper color initially
    ctx.fillStyle = '#1c1916';
    ctx.fillRect(0, 0, w, h);

    const blockSize = 12;
    const cols = Math.ceil(w / blockSize);
    const rows = Math.ceil(h / blockSize);
    const totalBlocks = rows * cols;

    // build reveal order: row by row, left to right, with slight stagger
    const order: { r: number; c: number; delay: number }[] = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const delay = r * 18 + c * 4 + Math.random() * 8;
        order.push({ r, c, delay });
      }
    }
    order.sort((a, b) => a.delay - b.delay);

    let startTime = 0;
    let raf: number;

    const animate = (t: number) => {
      if (!startTime) startTime = t;
      const elapsed = t - startTime;

      ctx.fillStyle = '#1c1916';
      ctx.fillRect(0, 0, w, h);

      let remaining = 0;
      for (const block of order) {
        const blockTime = block.delay;
        if (elapsed < blockTime) {
          // still visible
          ctx.fillStyle = '#1c1916';
          ctx.fillRect(block.c * blockSize, block.r * blockSize, blockSize, blockSize);
          remaining++;
        } else {
          // transitioning — show a brief coral flash then clear
          const age = elapsed - blockTime;
          if (age < 80) {
            const a = 1 - age / 80;
            ctx.fillStyle = `rgba(217,119,87,${a * 0.4})`;
            ctx.fillRect(block.c * blockSize, block.r * blockSize, blockSize, blockSize);
          }
          // else: fully cleared (transparent)
        }
      }

      if (remaining > 0) {
        raf = requestAnimationFrame(animate);
      } else {
        // final flash clear
        setTimeout(() => {
          setDone(true);
          onComplete?.();
        }, 100);
      }
    };

    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [active, onComplete]);

  return (
    <div className="relative">
      {children}
      {active && !done && (
        <canvas
          ref={overlayRef}
          className="fixed inset-0 z-[60] pointer-events-none"
          style={{ imageRendering: 'pixelated' }}
        />
      )}
    </div>
  );
}
