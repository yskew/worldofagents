import { useEffect, useRef } from 'react';

export default function PixelShield({ width = 200, height = 200 }: { width?: number; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const G = 64;
    c.width = G; c.height = G;
    c.style.width = width + 'px'; c.style.height = height + 'px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const shield = [
      '  ########  ',
      ' ########## ',
      '############',
      '############',
      '############',
      '############',
      ' ########## ',
      '  ########  ',
      '   ######   ',
      '    ####    ',
      '     ##     ',
    ];

    const scanParticles: { x: number; y: number; a: number }[] = [];
    let scanY = 0;
    let raf: number;

    const draw = () => {
      const t = performance.now() * 0.001;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, G, G);

      // draw shield
      const sx = Math.floor(G / 2 - 6);
      const sy = Math.floor(G / 2 - 6);
      const pulse = 0.6 + Math.sin(t * 2) * 0.15;

      for (let r = 0; r < shield.length; r++) {
        for (let col = 0; col < shield[r].length; col++) {
          if (shield[r][col] !== '#') continue;
          const px = sx + col;
          const py = sy + r;

          // color based on position — gradient top to bottom
          const ratio = r / shield.length;
          const cr = Math.floor(217 * pulse - ratio * 40);
          const cg = Math.floor(119 * pulse - ratio * 20);
          const cb = Math.floor(87 * pulse);
          ctx.fillStyle = `rgb(${cr},${cg},${cb})`;
          ctx.fillRect(px, py, 1, 1);
        }
      }

      // scanning line sweeping over the shield
      scanY = (scanY + 0.3) % (shield.length + 6);
      const lineY = sy + Math.floor(scanY) - 3;
      if (lineY >= sy && lineY < sy + shield.length) {
        ctx.fillStyle = 'rgba(125,204,138,0.5)';
        ctx.fillRect(sx - 2, lineY, shield[0].length + 4, 1);
        ctx.fillStyle = 'rgba(125,204,138,0.15)';
        ctx.fillRect(sx - 2, lineY - 1, shield[0].length + 4, 1);
        ctx.fillRect(sx - 2, lineY + 1, shield[0].length + 4, 1);

        // emit scan particles
        if (Math.random() > 0.5) {
          scanParticles.push({
            x: sx + Math.random() * shield[0].length,
            y: lineY,
            a: 1,
          });
        }
      }

      // draw/update scan particles
      for (let i = scanParticles.length - 1; i >= 0; i--) {
        const p = scanParticles[i];
        p.y -= 0.3;
        p.x += (Math.random() - 0.5) * 0.5;
        p.a -= 0.03;
        if (p.a <= 0) { scanParticles.splice(i, 1); continue; }
        ctx.fillStyle = `rgba(125,204,138,${p.a * 0.6})`;
        ctx.fillRect(Math.floor(p.x), Math.floor(p.y), 1, 1);
      }

      // rotating data dots around shield
      for (let i = 0; i < 8; i++) {
        const angle = t * 0.8 + (i * Math.PI * 2) / 8;
        const r = 14 + Math.sin(t * 1.5 + i) * 2;
        const dx = G / 2 + Math.cos(angle) * r;
        const dy = G / 2 + Math.sin(angle) * r;
        ctx.fillStyle = i % 2 === 0 ? 'rgba(217,119,87,0.4)' : 'rgba(232,155,125,0.3)';
        ctx.fillRect(Math.floor(dx), Math.floor(dy), 1, 1);
      }

      // corner brackets
      const bColor = `rgba(217,119,87,${0.2 + Math.sin(t * 3) * 0.1})`;
      ctx.fillStyle = bColor;
      // top-left
      ctx.fillRect(sx - 4, sy - 3, 4, 1);
      ctx.fillRect(sx - 4, sy - 3, 1, 4);
      // top-right
      ctx.fillRect(sx + shield[0].length, sy - 3, 4, 1);
      ctx.fillRect(sx + shield[0].length + 3, sy - 3, 1, 4);
      // bottom-left
      ctx.fillRect(sx - 4, sy + shield.length + 2, 4, 1);
      ctx.fillRect(sx - 4, sy + shield.length - 1, 1, 4);
      // bottom-right
      ctx.fillRect(sx + shield[0].length, sy + shield.length + 2, 4, 1);
      ctx.fillRect(sx + shield[0].length + 3, sy + shield.length - 1, 1, 4);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return <canvas ref={ref} />;
}
