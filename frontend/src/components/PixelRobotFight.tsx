import { useEffect, useRef } from 'react';

export default function PixelRobotFight({ width = 400, height = 120 }: { width?: number; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const GW = 160;
    const GH = 48;
    c.width = GW; c.height = GH;
    c.style.width = width + 'px'; c.style.height = height + 'px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const robotA = [
      ' ### ',
      '#o#o#',
      ' ### ',
      '##X##',
      ' ### ',
      ' # # ',
      ' # # ',
    ];

    const sparks: { x: number; y: number; vx: number; vy: number; life: number }[] = [];
    const beams: { x: number; y: number; dx: number; life: number }[] = [];
    let frame = 0;
    let raf: number;

    const drawBot = (sprite: string[], x: number, y: number, color: string, accent: string, flip: boolean) => {
      for (let r = 0; r < sprite.length; r++) {
        for (let col = 0; col < sprite[r].length; col++) {
          const ch = sprite[r][col];
          if (ch === ' ') continue;
          const px = flip ? x + (sprite[r].length - 1 - col) : x + col;
          const py = y + r;
          if (px < 0 || px >= GW || py < 0 || py >= GH) continue;
          if (ch === 'o') ctx.fillStyle = '#f0eee6';
          else if (ch === 'X') ctx.fillStyle = accent;
          else ctx.fillStyle = color;
          ctx.fillRect(px, py, 1, 1);
        }
      }
    };

    const draw = () => {
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, GW, GH);

      const floorY = GH - 5;

      // ground
      ctx.fillStyle = '#262220';
      ctx.fillRect(0, floorY, GW, 5);
      for (let i = 0; i < GW; i += 4) {
        ctx.fillStyle = '#312d29';
        ctx.fillRect(i, floorY, 2, 1);
      }

      // robots
      const bounce = Math.sin(frame * 0.08) * 1.5;
      const aX = GW / 2 - 25 + Math.sin(frame * 0.04) * 3;
      const bX = GW / 2 + 18 + Math.sin(frame * 0.04 + Math.PI) * 3;
      const aY = floorY - 8 + Math.floor(bounce);
      const bY = floorY - 8 + Math.floor(-bounce);

      drawBot(robotA, Math.floor(aX), Math.floor(aY), '#d97757', '#7dcc8a', false);
      drawBot(robotA, Math.floor(bX), Math.floor(bY), '#e89b7d', '#cc5f5f', true);

      // lasers
      if (frame % 45 === 0) beams.push({ x: aX + 5, y: aY + 3, dx: 1.5, life: 40 });
      if (frame % 45 === 22) beams.push({ x: bX, y: bY + 3, dx: -1.5, life: 40 });

      for (let i = beams.length - 1; i >= 0; i--) {
        const b = beams[i];
        b.x += b.dx; b.life--;
        if (b.life <= 0 || b.x < 0 || b.x > GW) { beams.splice(i, 1); continue; }

        const alpha = b.life / 40;
        ctx.fillStyle = b.dx > 0 ? `rgba(125,204,138,${alpha})` : `rgba(204,95,95,${alpha})`;
        ctx.fillRect(Math.floor(b.x), Math.floor(b.y), 3, 1);

        if ((b.dx > 0 && b.x > bX - 1) || (b.dx < 0 && b.x < aX + 6)) {
          for (let s = 0; s < 4; s++) {
            sparks.push({ x: b.x, y: b.y, vx: (Math.random() - 0.5) * 2, vy: (Math.random() - 0.5) * 2, life: 10 + Math.random() * 10 });
          }
          beams.splice(i, 1);
        }
      }

      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.x += s.vx; s.y += s.vy; s.vy += 0.05; s.life--;
        if (s.life <= 0) { sparks.splice(i, 1); continue; }
        ctx.fillStyle = `rgba(240,238,230,${s.life / 20})`;
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), 1, 1);
      }

      // "VS" in center
      ctx.fillStyle = '#5e524a';
      const vx = Math.floor(GW / 2 - 5), vy = 8;
      const vs = [
        [1,0,0,0,1,0,0,1,1,1],
        [1,0,0,0,1,0,1,0,0,0],
        [0,1,0,1,0,0,0,1,1,0],
        [0,0,1,0,0,0,0,0,0,1],
        [0,0,1,0,0,0,1,1,1,0],
      ];
      for (let r = 0; r < vs.length; r++)
        for (let col = 0; col < vs[r].length; col++)
          if (vs[r][col]) ctx.fillRect(vx + col, vy + r, 1, 1);

      // stars in background
      for (let i = 0; i < 12; i++) {
        const sx = (i * 13 + frame * 0.1) % GW;
        const sy = 3 + (i * 7) % 15;
        const a = 0.15 + Math.sin(frame * 0.02 + i) * 0.1;
        ctx.fillStyle = `rgba(138,122,111,${a})`;
        ctx.fillRect(Math.floor(sx), sy, 1, 1);
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return <canvas ref={ref} />;
}
