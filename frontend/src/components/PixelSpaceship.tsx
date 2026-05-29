import { useEffect, useRef } from 'react';

export default function PixelSpaceship({ width = 320, height = 120 }: { width?: number; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const G = 80;
    const gh = Math.floor(G * (height / width));
    c.width = G; c.height = gh;
    c.style.width = width + 'px'; c.style.height = height + 'px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const stars: { x: number; y: number; s: number; b: number }[] = [];
    for (let i = 0; i < 40; i++) stars.push({ x: Math.random() * G, y: Math.random() * gh, s: Math.random() * 2 + 0.5, b: Math.random() });

    const ship = [
      '   ##   ',
      '  ####  ',
      ' ###### ',
      '########',
      '# #### #',
      '  #  #  ',
      ' ##  ## ',
    ];

    let exhaust = 0;
    let shipX = -10;
    let raf: number;

    const draw = () => {
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, G, gh);

      // stars
      for (const s of stars) {
        s.x -= s.s * 0.4;
        if (s.x < 0) { s.x = G; s.y = Math.random() * gh; }
        const flicker = 0.4 + Math.sin(performance.now() * 0.003 * s.b + s.b * 10) * 0.3;
        const a = Math.floor(flicker * 255);
        ctx.fillStyle = s.s > 1.5 ? `rgba(217,119,87,${a / 255})` : `rgba(138,122,111,${a / 255})`;
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), s.s > 1.5 ? 2 : 1, 1);
      }

      // ship
      shipX += 0.15;
      if (shipX > G + 10) shipX = -10;
      const sy = Math.floor(gh / 2 - 3 + Math.sin(performance.now() * 0.002) * 2);
      const sx = Math.floor(shipX);
      exhaust = (exhaust + 1) % 4;

      for (let r = 0; r < ship.length; r++) {
        for (let col = 0; col < ship[r].length; col++) {
          if (ship[r][col] === '#') {
            const px = sx + col;
            const py = sy + r;
            if (px >= 0 && px < G && py >= 0 && py < gh) {
              ctx.fillStyle = r < 3 ? '#d97757' : '#e89b7d';
              ctx.fillRect(px, py, 1, 1);
            }
          }
        }
      }

      // exhaust flames
      for (let i = 0; i < 4; i++) {
        const ex = sx - 1 - i - (exhaust % 2);
        const ey = sy + 3 + Math.floor(Math.random() * 2);
        if (ex >= 0 && ex < G) {
          ctx.fillStyle = i < 2 ? '#d97757' : '#a8431f';
          ctx.fillRect(ex, ey, 1, 1);
        }
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return <canvas ref={ref} />;
}
