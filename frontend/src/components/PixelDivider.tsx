import { useEffect, useRef } from 'react';

export default function PixelDivider({ width = 800 }: { width?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const GW = 200;
    const GH = 6;
    c.width = GW; c.height = GH;
    c.style.width = width + 'px';
    c.style.height = '18px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    let raf: number;
    const draw = () => {
      const t = performance.now() * 0.001;
      ctx.clearRect(0, 0, GW, GH);

      // animated dashed line
      for (let i = 0; i < GW; i++) {
        const offset = Math.floor(t * 8) % 8;
        if ((i + offset) % 8 < 4) {
          const a = 0.15 + Math.sin(t * 0.5 + i * 0.05) * 0.08;
          ctx.fillStyle = `rgba(217,119,87,${a})`;
          ctx.fillRect(i, 2, 1, 2);
        }
      }

      // occasional bright dot
      const dotPos = Math.floor((t * 20) % GW);
      ctx.fillStyle = 'rgba(217,119,87,0.5)';
      ctx.fillRect(dotPos, 2, 2, 2);
      ctx.fillStyle = 'rgba(217,119,87,0.2)';
      ctx.fillRect(dotPos - 2, 2, 2, 2);
      ctx.fillRect(dotPos + 2, 2, 2, 2);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width]);

  return <canvas ref={ref} className="w-full" />;
}
