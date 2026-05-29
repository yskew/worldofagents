import { useEffect, useRef } from 'react';

export default function PixelKeyTheft({ active = true }: { active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 120, H = 64;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const lock = [
      '  ####  ',
      ' #    # ',
      '#      #',
      '########',
      '########',
      '###{}###',
      '########',
      '########',
    ];
    const key = [
      '  ##',
      '####',
      '#   ',
      '##  ',
    ];
    const robot = [
      ' ### ',
      '#o#o#',
      ' ### ',
      '##X##',
      ' ### ',
      ' # # ',
    ];

    let raf: number;
    let frame = 0;

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      const cycle = frame % 300;
      const lockX = 10, lockY = 20;

      // draw lock
      for (let r = 0; r < lock.length; r++) {
        for (let col = 0; col < lock[r].length; col++) {
          const ch = lock[r][col];
          if (ch === ' ') continue;
          ctx.fillStyle = ch === '{' || ch === '}' ? '#5e524a' : '#8a7a6f';
          ctx.fillRect(lockX + col, lockY + r, 1, 1);
        }
      }

      // key animation
      const keyProgress = Math.min(1, cycle / 120);
      const kx = lockX + 8 + keyProgress * 55;
      const ky = lockY + 2 + Math.sin(cycle * 0.05) * 3;

      if (cycle < 240) {
        for (let r = 0; r < key.length; r++) {
          for (let col = 0; col < key[r].length; col++) {
            if (key[r][col] === '#') {
              ctx.fillStyle = '#d97757';
              ctx.fillRect(Math.floor(kx) + col, Math.floor(ky) + r, 1, 1);
            }
          }
        }
      }

      // robot waiting on right
      const robotX = 85 + Math.sin(frame * 0.03) * 2;
      const robotY = 22;
      for (let r = 0; r < robot.length; r++) {
        for (let col = 0; col < robot[r].length; col++) {
          const ch = robot[r][col];
          if (ch === ' ') continue;
          ctx.fillStyle = ch === 'o' ? '#f0eee6' : ch === 'X' ? '#cc5f5f' : '#e89b7d';
          ctx.fillRect(Math.floor(robotX) + col, robotY + r, 1, 1);
        }
      }

      // warning ! when key reaches robot
      if (cycle > 100 && cycle < 240) {
        const flash = Math.sin(cycle * 0.15) > 0;
        if (flash) {
          ctx.fillStyle = '#cc5f5f';
          ctx.fillRect(Math.floor(robotX) + 2, robotY - 4, 1, 2);
          ctx.fillRect(Math.floor(robotX) + 2, robotY - 1, 1, 1);
        }
      }

      // key cloning effect
      if (cycle > 180 && cycle < 280) {
        const cloneP = (cycle - 180) / 100;
        for (let i = 0; i < 3; i++) {
          const angle = (i * Math.PI * 2) / 3 + cloneP * 2;
          const cx = Math.floor(robotX) + 2 + Math.cos(angle) * cloneP * 15;
          const cy = robotY + 2 + Math.sin(angle) * cloneP * 10;
          const a = 1 - cloneP;
          ctx.fillStyle = `rgba(217,119,87,${a})`;
          ctx.fillRect(Math.floor(cx), Math.floor(cy), 2, 1);
          ctx.fillRect(Math.floor(cx) - 1, Math.floor(cy) + 1, 4, 1);
        }
      }

      // stars
      for (let i = 0; i < 8; i++) {
        const sx = (i * 17 + 3) % W;
        const sy = (i * 11 + 5) % H;
        const a = 0.1 + Math.sin(frame * 0.02 + i) * 0.08;
        ctx.fillStyle = `rgba(138,122,111,${a})`;
        ctx.fillRect(sx, sy, 1, 1);
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active]);

  return <canvas ref={ref} className="w-[400px] h-[213px]" />;
}
