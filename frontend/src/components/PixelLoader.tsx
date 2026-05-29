import { useEffect, useRef } from 'react';

export default function PixelLoader({ text = 'LOADING' }: { text?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const G = 80;
    c.width = G; c.height = 40;
    c.style.width = '240px'; c.style.height = '120px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    // a little satellite orbiting
    const sat = [
      '#_#',
      '_#_',
      '#_#',
    ];

    const stars: { x: number; y: number }[] = [];
    for (let i = 0; i < 20; i++) stars.push({ x: Math.random() * G, y: Math.random() * 40 });

    let raf: number;
    const draw = () => {
      const t = performance.now() * 0.001;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, G, 40);

      // stars twinkle
      for (const s of stars) {
        const a = 0.15 + Math.sin(t * 2 + s.x * 0.5) * 0.15;
        ctx.fillStyle = `rgba(138,122,111,${a})`;
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), 1, 1);
      }

      // orbiting satellite
      const cx = G / 2, cy = 16;
      const orbitR = 10;
      const angle = t * 1.2;
      const sx = cx + Math.cos(angle) * orbitR;
      const sy = cy + Math.sin(angle) * orbitR * 0.4;

      // orbit trail
      for (let i = 0; i < 12; i++) {
        const a2 = angle - i * 0.15;
        const tx = cx + Math.cos(a2) * orbitR;
        const ty = cy + Math.sin(a2) * orbitR * 0.4;
        const alpha = (12 - i) / 12 * 0.2;
        ctx.fillStyle = `rgba(217,119,87,${alpha})`;
        ctx.fillRect(Math.floor(tx), Math.floor(ty), 1, 1);
      }

      // satellite
      for (let r = 0; r < sat.length; r++) {
        for (let col = 0; col < sat[r].length; col++) {
          if (sat[r][col] === '#') {
            ctx.fillStyle = '#d97757';
            ctx.fillRect(Math.floor(sx) - 1 + col, Math.floor(sy) - 1 + r, 1, 1);
          }
        }
      }

      // solar panel glow
      ctx.fillStyle = `rgba(217,119,87,${0.3 + Math.sin(t * 4) * 0.2})`;
      ctx.fillRect(Math.floor(sx) - 1, Math.floor(sy), 1, 1);
      ctx.fillRect(Math.floor(sx) + 1, Math.floor(sy), 1, 1);

      // loading dots
      const dotY = 32;
      const dots = 3;
      const active = Math.floor(t * 3) % (dots + 1);
      for (let i = 0; i < dots; i++) {
        const dx = G / 2 - 3 + i * 3;
        ctx.fillStyle = i < active ? '#d97757' : '#312d29';
        ctx.fillRect(dx, dotY, 2, 2);
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="flex flex-col items-center gap-3">
      <canvas ref={ref} />
      <span className="text-[10px] text-dim tracking-[0.2em] font-[Silkscreen]">{text}</span>
    </div>
  );
}
