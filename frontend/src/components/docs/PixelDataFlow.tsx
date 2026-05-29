import { useEffect, useRef } from 'react';

export default function PixelDataFlow({ active = true }: { active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 160, H = 60;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const human = [' ## ', '#  #', '####', ' ## ', ' ## '];
    const server = ['######', '#    #', '# {} #', '#    #', '######'];
    const db = [' #### ', '######', '#    #', '######', ' #### '];
    const robot = [' ### ', '#o#o#', ' ### ', '##X##', ' ### '];

    let raf: number;
    let frame = 0;

    const drawSprite = (sprite: string[], x: number, y: number, color: string, accent?: string) => {
      for (let r = 0; r < sprite.length; r++) {
        for (let col = 0; col < sprite[r].length; col++) {
          const ch = sprite[r][col];
          if (ch === ' ') continue;
          ctx.fillStyle = (ch === '{' || ch === '}' || ch === 'o') ? (accent || '#f0eee6') : ch === 'X' ? '#cc5f5f' : color;
          ctx.fillRect(x + col, y + r, 1, 1);
        }
      }
    };

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      const cycle = frame % 400;
      const isVerify = cycle >= 200;
      const phase = isVerify ? (cycle - 200) / 200 : cycle / 200;

      // positions
      const hx = 10, hy = 20;
      const sx = 68, sy = 18;
      const dx = 130, dy = 20;

      // sprites
      drawSprite(human, hx, hy, '#e89b7d');
      drawSprite(server, sx, sy, '#8a7a6f', '#d97757');
      drawSprite(db, dx, dy, '#5e524a');

      // robot appears in verify phase
      if (isVerify) {
        drawSprite(robot, hx + 8, hy - 2, '#d97757', '#f0eee6');
      }

      // flowing dots: source → server
      const dotCount = 5;
      for (let i = 0; i < dotCount; i++) {
        const dp = (phase * 2 + i / dotCount) % 1;
        if (dp > 0.5) continue;
        const p = dp * 2;
        const fx = hx + 6 + p * (sx - hx - 6);
        const fy = hy + 2 + Math.sin(p * Math.PI) * -4;
        ctx.fillStyle = isVerify ? 'rgba(125,204,138,0.6)' : 'rgba(217,119,87,0.6)';
        ctx.fillRect(Math.floor(fx), Math.floor(fy), 1, 1);
      }

      // flowing dots: server → db (registration) or server → output (verify)
      for (let i = 0; i < dotCount; i++) {
        const dp = (phase * 2 + i / dotCount) % 1;
        if (dp < 0.5) continue;
        const p = (dp - 0.5) * 2;
        const fx = sx + 6 + p * (dx - sx - 6);
        const fy = sy + 2 + Math.sin(p * Math.PI) * -3;
        ctx.fillStyle = isVerify ? 'rgba(125,204,138,0.4)' : 'rgba(232,155,125,0.5)';
        ctx.fillRect(Math.floor(fx), Math.floor(fy), 1, 1);
      }

      // output indicator
      if (phase > 0.7) {
        const outAlpha = (phase - 0.7) / 0.3;
        if (isVerify) {
          // JWT checkmark
          ctx.fillStyle = `rgba(125,204,138,${outAlpha})`;
          ctx.fillRect(dx + 1, dy - 5, 1, 1);
          ctx.fillRect(dx + 2, dy - 4, 1, 1);
          ctx.fillRect(dx + 3, dy - 5, 1, 1);
          ctx.fillRect(dx + 4, dy - 6, 1, 1);
        } else {
          // key + fingerprint icons
          ctx.fillStyle = `rgba(217,119,87,${outAlpha})`;
          ctx.fillRect(dx + 1, dy - 5, 3, 1);
          ctx.fillRect(dx + 1, dy - 4, 1, 1);
        }
      }

      // phase label
      ctx.fillStyle = isVerify ? '#7dcc8a' : '#d97757';
      ctx.fillRect(W / 2 - 8, 5, 2, 2);
      ctx.fillRect(W / 2 - 4, 5, 2, 2);
      ctx.fillRect(W / 2, 5, 2, 2);
      ctx.fillRect(W / 2 + 4, 5, 2, 2);

      // ground
      ctx.fillStyle = '#1c1916';
      ctx.fillRect(0, H - 4, W, 4);
      for (let i = 0; i < W; i += 6) {
        ctx.fillStyle = '#262220';
        ctx.fillRect(i, H - 4, 3, 1);
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active]);

  return <canvas ref={ref} className="w-[520px] h-[195px]" />;
}
