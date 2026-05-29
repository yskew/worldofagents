import { useEffect, useRef } from 'react';

export default function PixelAstronaut({ width = 200, height = 180, text = 'NOTHING HERE YET' }: { width?: number; height?: number; text?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const G = 64;
    const gh = Math.floor(G * (height / width));
    c.width = G; c.height = gh;
    c.style.width = width + 'px'; c.style.height = height + 'px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const astro = [
      '  ####  ',
      ' #    # ',
      '#  ##  #',
      '#  ##  #',
      ' #    # ',
      '  ####  ',
      ' ##  ## ',
      '##    ##',
      '#  ##  #',
      '   ##   ',
      '  #  #  ',
      '  #  #  ',
    ];

    const stars: { x: number; y: number; b: number }[] = [];
    for (let i = 0; i < 30; i++) stars.push({ x: Math.random() * G, y: Math.random() * gh, b: Math.random() });

    let raf: number;
    const draw = () => {
      const t = performance.now() * 0.001;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, G, gh);

      // stars
      for (const s of stars) {
        const a = 0.1 + Math.sin(t * 1.5 + s.b * 10) * 0.15;
        ctx.fillStyle = `rgba(138,122,111,${a})`;
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), 1, 1);
      }

      // floating astronaut
      const ax = G / 2 - 4;
      const ay = gh / 2 - 8 + Math.sin(t * 0.7) * 3;
      const rot = Math.sin(t * 0.3) * 0.03;

      for (let r = 0; r < astro.length; r++) {
        for (let col = 0; col < astro[r].length; col++) {
          if (astro[r][col] === ' ') continue;
          const px = ax + col + rot * (r - 6) * 2;
          const py = ay + r;
          if (r < 6) {
            ctx.fillStyle = '#f0eee6'; // helmet
          } else if (r < 9) {
            ctx.fillStyle = '#e89b7d'; // suit
          } else {
            ctx.fillStyle = '#d97757'; // legs
          }
          ctx.fillRect(Math.floor(px), Math.floor(py), 1, 1);
        }
      }

      // visor reflection
      ctx.fillStyle = `rgba(125,204,138,${0.3 + Math.sin(t * 2) * 0.15})`;
      ctx.fillRect(Math.floor(ax) + 3, Math.floor(ay) + 2, 2, 2);

      // tether line
      ctx.fillStyle = '#3a3530';
      for (let i = 0; i < 10; i++) {
        const tx = ax - 2 - i * 1.5;
        const ty = ay + 4 + Math.sin(t * 0.5 + i * 0.5) * 1.5;
        ctx.fillRect(Math.floor(tx), Math.floor(ty), 1, 1);
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return (
    <div className="flex flex-col items-center gap-3">
      <canvas ref={ref} />
      <span className="text-[10px] text-dim tracking-[0.2em] font-[Silkscreen]">{text}</span>
    </div>
  );
}
