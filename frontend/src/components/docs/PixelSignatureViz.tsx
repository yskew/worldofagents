import { useEffect, useRef } from 'react';

export default function PixelSignatureViz({ active = true }: { active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current!;
    const W = 160, H = 80;
    c.width = W; c.height = H;
    c.style.imageRendering = 'pixelated';
    const ctx = c.getContext('2d')!;

    const barNames = ['SRCH', 'READ', 'EDIT', 'TEST', 'MSG'];
    const barHeights = [0.7, 0.85, 0.6, 0.4, 0.55];

    const fpTargets: { x: number; y: number }[] = [];
    for (let i = 0; i < 20; i++) {
      const a = (i / 20) * Math.PI * 2;
      const r = 6 + (i % 3) * 2;
      fpTargets.push({ x: 135 + Math.cos(a) * r, y: 40 + Math.sin(a) * r });
    }

    let raf: number;
    let frame = 0;

    const draw = () => {
      if (!active) { raf = requestAnimationFrame(draw); return; }
      frame++;
      const t = frame * 0.01;
      ctx.fillStyle = '#141210';
      ctx.fillRect(0, 0, W, H);

      // --- histogram bars (left section) ---
      const barW = 6, barGap = 3, barBaseY = 68, barMaxH = 40;
      const barStartX = 8;

      for (let i = 0; i < barNames.length; i++) {
        const x = barStartX + i * (barW + barGap);
        const targetH = barHeights[i] * barMaxH;
        const animH = targetH * Math.min(1, t * 0.5 + i * 0.1);
        const wobble = Math.sin(frame * 0.03 + i * 1.5) * 1.5;
        const h = Math.floor(animH + wobble);

        // bar
        ctx.fillStyle = '#d97757';
        ctx.fillRect(x, barBaseY - h, barW, h);

        // bar highlight
        ctx.fillStyle = '#e89b7d';
        ctx.fillRect(x, barBaseY - h, barW, 1);

        // label dot
        ctx.fillStyle = '#5e524a';
        ctx.fillRect(x + 2, barBaseY + 2, 2, 1);
      }

      // baseline
      ctx.fillStyle = '#312d29';
      ctx.fillRect(barStartX - 2, barBaseY, barNames.length * (barW + barGap) + 2, 1);

      // --- flow arrows (center section) ---
      const arrowStartX = 58, arrowEndX = 115;
      const arrowY = 35;
      const numArrows = 3;

      for (let i = 0; i < numArrows; i++) {
        const yOff = (i - 1) * 12;
        // dashed line
        for (let x = arrowStartX; x < arrowEndX; x += 3) {
          ctx.fillStyle = `rgba(138,122,111,0.2)`;
          ctx.fillRect(x, arrowY + yOff, 2, 1);
        }

        // moving dot
        const dotPhase = ((frame * 0.8 + i * 40) % (arrowEndX - arrowStartX));
        const dotX = arrowStartX + dotPhase;
        ctx.fillStyle = i === 1 ? '#d97757' : '#e89b7d';
        ctx.fillRect(Math.floor(dotX), arrowY + yOff - 1, 2, 3);

        // trail
        for (let t = 1; t < 5; t++) {
          const trailX = dotX - t * 3;
          if (trailX >= arrowStartX) {
            ctx.fillStyle = `rgba(217,119,87,${0.3 - t * 0.06})`;
            ctx.fillRect(Math.floor(trailX), arrowY + yOff, 1, 1);
          }
        }
      }

      // arrow label
      ctx.fillStyle = '#5e524a';
      ctx.fillRect(80, arrowY - 18, 1, 1);
      ctx.fillRect(82, arrowY - 18, 1, 1);
      ctx.fillRect(84, arrowY - 18, 1, 1);

      // --- fingerprint (right section) ---
      const fpCenterX = 135, fpCenterY = 40;

      for (let i = 0; i < fpTargets.length; i++) {
        const target = fpTargets[i];
        const assembleProgress = Math.min(1, t * 0.3 - i * 0.02);

        if (assembleProgress <= 0) continue;

        const scatterR = 20 * (1 - assembleProgress);
        const angle = i * 1.3 + frame * 0.01;
        const sx = target.x + Math.cos(angle) * scatterR;
        const sy = target.y + Math.sin(angle) * scatterR;

        const a = assembleProgress * 0.8;
        ctx.fillStyle = `rgba(217,119,87,${a})`;
        ctx.fillRect(Math.floor(sx), Math.floor(sy), 1, 1);
      }

      // center dot
      if (t > 1) {
        const centerAlpha = Math.min(1, t - 1) * (0.5 + Math.sin(frame * 0.05) * 0.3);
        ctx.fillStyle = `rgba(217,119,87,${centerAlpha})`;
        ctx.fillRect(fpCenterX - 1, fpCenterY - 1, 3, 3);
      }

      // section labels at top
      ctx.fillStyle = '#5e524a';
      // "HIST" area
      ctx.fillRect(20, 5, 2, 1); ctx.fillRect(23, 5, 2, 1);
      // "FLOW" area
      ctx.fillRect(82, 5, 2, 1); ctx.fillRect(85, 5, 2, 1);
      // "PRINT" area
      ctx.fillRect(130, 5, 2, 1); ctx.fillRect(133, 5, 2, 1);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [active]);

  return <canvas ref={ref} className="w-[480px] h-[240px]" />;
}
