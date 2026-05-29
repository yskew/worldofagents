import { useEffect, useRef } from 'react';

export default function PixelTimeline({ active = true }: { active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 160, H = 50;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const nodes = [
      { x: 30, label: '90D', icon: 'shield' },
      { x: 80, label: '180D', icon: 'network' },
      { x: 130, label: '365D', icon: 'globe' },
    ];

    let raf: number;
    let frame = 0;

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      const lineY = 25;

      // dashed timeline
      for (let x = 10; x < 150; x += 3) {
        ctx.fillStyle = '#312d29';
        ctx.fillRect(x, lineY, 2, 1);
      }

      // nodes
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        const lightUpTime = i * 80 + 40;
        const lit = frame > lightUpTime;
        const fadeIn = lit ? Math.min(1, (frame - lightUpTime) / 40) : 0;

        // node square
        ctx.fillStyle = lit ? '#d97757' : '#3a3530';
        ctx.globalAlpha = lit ? fadeIn : 0.5;
        ctx.fillRect(node.x - 3, lineY - 3, 7, 7);
        ctx.globalAlpha = 1;

        // inner
        if (lit) {
          ctx.fillStyle = '#1c1916';
          ctx.fillRect(node.x - 2, lineY - 2, 5, 5);
          ctx.fillStyle = `rgba(217,119,87,${fadeIn * 0.5})`;
          ctx.fillRect(node.x - 1, lineY - 1, 3, 3);
        }

        // glow
        if (lit) {
          ctx.fillStyle = `rgba(217,119,87,${fadeIn * 0.15})`;
          ctx.fillRect(node.x - 5, lineY - 5, 11, 11);
        }

        // label above
        ctx.fillStyle = lit ? '#e89b7d' : '#5e524a';
        ctx.globalAlpha = lit ? fadeIn : 0.4;
        // pixel dots for label
        for (let d = 0; d < 3; d++) {
          ctx.fillRect(node.x - 2 + d * 2, lineY - 8, 1, 1);
        }
        ctx.globalAlpha = 1;

        // icon below
        if (lit && fadeIn > 0.5) {
          const iconAlpha = (fadeIn - 0.5) * 2;
          ctx.globalAlpha = iconAlpha;
          if (node.icon === 'shield') {
            ctx.fillStyle = '#7dcc8a';
            ctx.fillRect(node.x - 2, lineY + 8, 5, 1);
            ctx.fillRect(node.x - 2, lineY + 9, 5, 1);
            ctx.fillRect(node.x - 1, lineY + 10, 3, 1);
            ctx.fillRect(node.x, lineY + 11, 1, 1);
          } else if (node.icon === 'network') {
            ctx.fillStyle = '#ccaa44';
            ctx.fillRect(node.x, lineY + 8, 1, 1);
            ctx.fillRect(node.x - 2, lineY + 10, 1, 1);
            ctx.fillRect(node.x + 2, lineY + 10, 1, 1);
            ctx.fillRect(node.x - 1, lineY + 9, 1, 1);
            ctx.fillRect(node.x + 1, lineY + 9, 1, 1);
          } else {
            ctx.fillStyle = '#d97757';
            ctx.fillRect(node.x - 1, lineY + 8, 3, 1);
            ctx.fillRect(node.x - 2, lineY + 9, 5, 1);
            ctx.fillRect(node.x - 2, lineY + 10, 5, 1);
            ctx.fillRect(node.x - 1, lineY + 11, 3, 1);
          }
          ctx.globalAlpha = 1;
        }
      }

      // traveling dot
      const dotCycle = (frame * 0.5) % 160;
      if (dotCycle > 10 && dotCycle < 150) {
        ctx.fillStyle = '#d97757';
        ctx.fillRect(Math.floor(dotCycle), lineY, 2, 1);
        // trail
        for (let t = 1; t < 6; t++) {
          ctx.fillStyle = `rgba(217,119,87,${0.3 - t * 0.05})`;
          ctx.fillRect(Math.floor(dotCycle) - t * 2, lineY, 1, 1);
        }
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active]);

  return <canvas ref={ref} className="w-[520px] h-[160px]" />;
}
