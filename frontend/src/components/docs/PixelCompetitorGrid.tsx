import { useEffect, useRef } from 'react';

export default function PixelCompetitorGrid({ active = true }: { active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 120, H = 80;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const grid = [
      { label: 'IETF', color: '#ccaa44', row: 0, col: 0 },
      { label: 'AIP', color: '#ccaa44', row: 0, col: 1 },
      { label: 'OIDC', color: '#ccaa44', row: 0, col: 2 },
      { label: 'NIST', color: '#ccaa44', row: 0, col: 3 },
      { label: 'ZeroID', color: '#7dcc8a', row: 1, col: 0 },
      { label: 'AIP-OS', color: '#7dcc8a', row: 1, col: 1 },
      { label: 'MS-AGT', color: '#7dcc8a', row: 1, col: 2 },
      { label: 'WoA', color: '#d97757', row: 1, col: 3 },
      { label: 'Entra', color: '#cc5f5f', row: 2, col: 0 },
      { label: 'Vertex', color: '#cc5f5f', row: 2, col: 1 },
      { label: 'Okta', color: '#cc5f5f', row: 2, col: 2 },
      { label: 'Auth0', color: '#cc5f5f', row: 2, col: 3 },
    ];

    let raf: number;
    let frame = 0;

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      const cellW = 24, cellH = 18;
      const startX = 10, startY = 10;

      for (let i = 0; i < grid.length; i++) {
        const cell = grid[i];
        const x = startX + cell.col * (cellW + 3);
        const y = startY + cell.row * (cellH + 3);

        const lightUpFrame = i * 20;
        const lit = frame > lightUpFrame;
        const fadeIn = lit ? Math.min(1, (frame - lightUpFrame) / 30) : 0;

        // cell background
        ctx.fillStyle = '#1c1916';
        ctx.fillRect(x, y, cellW, cellH);

        // border
        const isWoA = cell.label === 'WoA';
        const borderAlpha = isWoA ? 0.5 + Math.sin(frame * 0.06) * 0.3 : fadeIn * 0.3;
        ctx.fillStyle = lit ? cell.color : '#262220';
        ctx.globalAlpha = lit ? borderAlpha : 0.2;
        ctx.fillRect(x, y, cellW, 1);
        ctx.fillRect(x, y + cellH - 1, cellW, 1);
        ctx.fillRect(x, y, 1, cellH);
        ctx.fillRect(x + cellW - 1, y, 1, cellH);
        ctx.globalAlpha = 1;

        // inner glow
        if (lit) {
          ctx.fillStyle = cell.color;
          ctx.globalAlpha = fadeIn * (isWoA ? 0.15 : 0.06);
          ctx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);
          ctx.globalAlpha = 1;
        }

        // center dot
        if (lit) {
          ctx.fillStyle = cell.color;
          ctx.globalAlpha = fadeIn;
          ctx.fillRect(x + cellW / 2 - 1, y + cellH / 2 - 1, 2, 2);
          ctx.globalAlpha = 1;
        }

        // WoA special pulse
        if (isWoA && lit) {
          const pulseR = 3 + Math.sin(frame * 0.04) * 2;
          ctx.fillStyle = `rgba(217,119,87,${0.1 + Math.sin(frame * 0.06) * 0.05})`;
          for (let a = 0; a < 8; a++) {
            const angle = (a / 8) * Math.PI * 2 + frame * 0.02;
            const px = x + cellW / 2 + Math.cos(angle) * pulseR;
            const py = y + cellH / 2 + Math.sin(angle) * pulseR;
            ctx.fillRect(Math.floor(px), Math.floor(py), 1, 1);
          }
        }
      }

      // row labels
      ctx.fillStyle = '#5e524a';
      ctx.fillRect(3, startY + 7, 4, 1);
      ctx.fillRect(3, startY + cellH + 3 + 7, 4, 1);
      ctx.fillRect(3, startY + (cellH + 3) * 2 + 7, 4, 1);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active]);

  return <canvas ref={ref} className="w-[400px] h-[265px]" />;
}
