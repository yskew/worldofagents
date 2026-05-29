import { useEffect, useRef } from 'react';

export default function PixelFactory({ width = 400, height = 140 }: { width?: number; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const G = 120;
    const gh = Math.floor(G * (height / width));
    c.width = G; c.height = gh;
    c.style.width = width + 'px'; c.style.height = height + 'px';
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    // conveyor belt items — little robot heads being assembled
    const items: { x: number; stage: number }[] = [];
    let spawnTimer = 0;

    const robotHead = [
      ' ### ',
      '#o#o#',
      ' ### ',
    ];

    const arm = [
      '##',
      ' #',
      ' #',
      '##',
    ];

    let raf: number;
    let frame = 0;

    const draw = () => {
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, G, gh);

      const floorY = gh - 6;

      // factory background — gears
      const gearT = performance.now() * 0.001;
      for (let gi = 0; gi < 3; gi++) {
        const gx = 15 + gi * 40;
        const gy = 10;
        const gr = 5;
        const spokes = 6;
        const rot = gearT * (gi % 2 === 0 ? 1 : -1) * 0.5;
        ctx.fillStyle = '#262220';
        for (let s = 0; s < spokes; s++) {
          const a = rot + (s * Math.PI * 2) / spokes;
          const dx = Math.cos(a) * gr;
          const dy = Math.sin(a) * gr;
          ctx.fillRect(Math.floor(gx + dx * 0.3), Math.floor(gy + dy * 0.3), 2, 2);
          ctx.fillRect(Math.floor(gx + dx * 0.7), Math.floor(gy + dy * 0.7), 1, 1);
          ctx.fillRect(Math.floor(gx + dx), Math.floor(gy + dy), 1, 1);
        }
        ctx.fillRect(gx, gy, 2, 2);
      }

      // conveyor belt
      ctx.fillStyle = '#312d29';
      ctx.fillRect(0, floorY, G, 2);
      for (let i = 0; i < G; i += 4) {
        const offset = Math.floor(frame * 0.3) % 4;
        ctx.fillStyle = '#3a3530';
        ctx.fillRect(((i + offset) % G), floorY, 2, 2);
      }

      // floor
      ctx.fillStyle = '#1c1916';
      ctx.fillRect(0, floorY + 2, G, gh - floorY - 2);

      // spawn items
      spawnTimer++;
      if (spawnTimer > 80) {
        items.push({ x: -8, stage: 0 });
        spawnTimer = 0;
      }

      // robot arms at stations
      const stations = [25, 55, 85];
      for (let si = 0; si < stations.length; si++) {
        const sx = stations[si];
        const armBob = Math.sin(frame * 0.06 + si * 2) * 3;
        const ay = floorY - 12 + Math.floor(armBob);

        // arm body
        ctx.fillStyle = '#5e524a';
        for (let r = 0; r < arm.length; r++) {
          for (let col = 0; col < arm[r].length; col++) {
            if (arm[r][col] === '#') ctx.fillRect(sx + col, ay + r, 1, 1);
          }
        }

        // arm base (ceiling mount)
        ctx.fillStyle = '#3a3530';
        ctx.fillRect(sx - 1, 0, 4, ay > 3 ? 3 : ay);
        ctx.fillStyle = '#5e524a';
        ctx.fillRect(sx, 0, 2, ay);

        // spark when arm is down
        if (armBob > 2) {
          ctx.fillStyle = `rgba(217,119,87,${0.5 + Math.random() * 0.5})`;
          ctx.fillRect(sx + Math.floor(Math.random() * 3), ay + 4, 1, 1);
          ctx.fillRect(sx + Math.floor(Math.random() * 3), ay + 5, 1, 1);
        }
      }

      // draw and move items
      for (let i = items.length - 1; i >= 0; i--) {
        const item = items[i];
        item.x += 0.3;
        if (item.x > G + 10) { items.splice(i, 1); continue; }

        // determine stage by position
        item.stage = item.x < 30 ? 0 : item.x < 60 ? 1 : item.x < 90 ? 2 : 3;

        const ix = Math.floor(item.x);
        const iy = floorY - 4;

        if (item.stage === 0) {
          // just a block
          ctx.fillStyle = '#a8431f';
          ctx.fillRect(ix, iy, 3, 3);
        } else if (item.stage === 1) {
          // partial head
          ctx.fillStyle = '#d97757';
          ctx.fillRect(ix, iy - 1, 5, 4);
        } else {
          // full robot head
          for (let r = 0; r < robotHead.length; r++) {
            for (let col = 0; col < robotHead[r].length; col++) {
              const ch = robotHead[r][col];
              if (ch === ' ') continue;
              ctx.fillStyle = ch === 'o' ? '#f0eee6' : (item.stage === 3 ? '#7dcc8a' : '#d97757');
              ctx.fillRect(ix + col, iy - 1 + r, 1, 1);
            }
          }
        }
      }

      // label
      ctx.fillStyle = '#5e524a';
      ctx.fillRect(2, 2, 1, 1);
      ctx.fillRect(4, 2, 1, 1);
      ctx.fillRect(6, 2, 1, 1);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return <canvas ref={ref} />;
}
