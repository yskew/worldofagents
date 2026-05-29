import { useEffect, useRef } from 'react';

interface Props {
  direction?: 'left' | 'right';
}

export default function PixelDivider({ direction = 'right' }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    let GW = 400;
    const GH = 6;
    const dir = direction === 'right' ? 1 : -1;

    function resize() {
      GW = Math.ceil(window.innerWidth / 4);
      c.width = GW;
      c.height = GH;
      c.style.imageRendering = 'pixelated';
    }
    resize();
    window.addEventListener('resize', resize);
    const ctx = c.getContext('2d')!;

    let raf: number;
    const draw = () => {
      const t = performance.now() * 0.001;
      ctx.clearRect(0, 0, GW, GH);

      for (let i = 0; i < GW; i++) {
        const offset = Math.floor(t * 8 * dir) % 8;
        if (((i + offset) % 8 + 8) % 8 < 4) {
          const a = 0.15 + Math.sin(t * 0.5 + i * 0.05) * 0.08;
          ctx.fillStyle = `rgba(217,119,87,${a})`;
          ctx.fillRect(i, 2, 1, 2);
        }
      }

      const dotPos = ((Math.floor(t * 20 * dir) % GW) + GW) % GW;
      ctx.fillStyle = 'rgba(217,119,87,0.5)';
      ctx.fillRect(dotPos, 2, 2, 2);
      ctx.fillStyle = 'rgba(217,119,87,0.2)';
      ctx.fillRect(dotPos - 2, 2, 2, 2);
      ctx.fillRect(dotPos + 2, 2, 2, 2);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, [direction]);

  return <canvas ref={ref} className="w-screen h-[18px]" style={{ imageRendering: 'pixelated' }} />;
}
