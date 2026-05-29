import { useEffect, useRef } from 'react';

export default function PixelLayerStack({ active = true, progress = 1 }: { active?: boolean; progress?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 100, H = 80;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const layers = [
      { label: 'AUTH', color: '#7dcc8a', threshold: 0.8 },
      { label: 'RUNTIME', color: '#d97757', threshold: 0.6 },
      { label: 'BINDING', color: '#d97757', threshold: 0.4 },
      { label: 'HUMAN', color: '#7dcc8a', threshold: 0.2 },
    ];

    let raf: number;
    let frame = 0;

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      const baseX = 15, baseY = 65, layerW = 70, layerH = 10, gap = 3;

      for (let i = 0; i < layers.length; i++) {
        const layer = layers[i];
        const visible = progress >= layer.threshold;
        if (!visible) continue;

        const fadeIn = Math.min(1, (progress - layer.threshold) / 0.15);
        const y = baseY - (3 - i) * (layerH + gap);
        const slideY = y + (1 - fadeIn) * 10;

        const isNew = layer.color === '#d97757';
        const pulse = isNew ? 0.7 + Math.sin(frame * 0.05 + i) * 0.3 : 1;

        // layer block
        ctx.globalAlpha = fadeIn * pulse;
        ctx.fillStyle = layer.color;
        ctx.fillRect(baseX, Math.floor(slideY), layerW, layerH);

        // border
        ctx.fillStyle = '#141210';
        ctx.fillRect(baseX + 1, Math.floor(slideY) + 1, layerW - 2, layerH - 2);
        ctx.fillStyle = layer.color;
        ctx.globalAlpha = fadeIn * pulse * 0.3;
        ctx.fillRect(baseX + 1, Math.floor(slideY) + 1, layerW - 2, layerH - 2);

        // label
        ctx.globalAlpha = fadeIn;
        ctx.fillStyle = isNew ? '#d97757' : '#7dcc8a';
        const labelX = baseX + 3;
        const labelY = Math.floor(slideY) + 4;
        // simple pixel text - just a marker dot + label position
        ctx.fillRect(labelX, labelY, 2, 2);
        ctx.fillRect(labelX + 4, labelY, 1, 2);
        ctx.fillRect(labelX + 6, labelY, 1, 2);
        ctx.fillRect(labelX + 8, labelY, 1, 2);

        // "NEW" tag for novel layers
        if (isNew && fadeIn > 0.8) {
          ctx.fillStyle = `rgba(217,119,87,${0.5 + Math.sin(frame * 0.08) * 0.3})`;
          ctx.fillRect(baseX + layerW - 12, Math.floor(slideY) + 3, 8, 4);
        }

        ctx.globalAlpha = 1;
      }

      // connectors between layers
      if (progress > 0.5) {
        const connAlpha = Math.min(1, (progress - 0.5) / 0.3) * 0.3;
        ctx.fillStyle = `rgba(138,122,111,${connAlpha})`;
        for (let i = 0; i < 3; i++) {
          const y1 = baseY - (3 - i) * (layerH + gap) + layerH;
          const y2 = baseY - (2 - i) * (layerH + gap);
          for (let dy = y1; dy < y2; dy += 2) {
            ctx.fillRect(baseX + layerW / 2, dy, 1, 1);
          }
        }
      }

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active, progress]);

  return <canvas ref={ref} className="w-[350px] h-[280px]" />;
}
