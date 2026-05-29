import { useEffect, useRef } from 'react';

interface Props {
  score: number;
  size?: number;
  label?: string;
}

export default function ScoreArc({ score, size = 120, label }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = canvasRef.current!;
    const ctx = c.getContext('2d')!;
    const dpr = Math.min(devicePixelRatio, 2);
    c.width = size * dpr;
    c.height = size * dpr;
    c.style.width = size + 'px';
    c.style.height = size + 'px';
    ctx.scale(dpr, dpr);

    const cx = size / 2, cy = size / 2, r = size * 0.38;
    const lw = 5;
    const startAngle = Math.PI * 0.75;
    const totalAngle = Math.PI * 1.5;

    // track
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, startAngle + totalAngle);
    ctx.strokeStyle = '#312d29';
    ctx.lineWidth = lw;
    ctx.lineCap = 'butt';
    ctx.stroke();

    // filled arc
    const color = score >= 0.7 ? '#7dcc8a' : score >= 0.4 ? '#ccaa44' : '#cc5f5f';
    const glow = score >= 0.7 ? 'rgba(125,204,138,0.4)' : score >= 0.4 ? 'rgba(204,170,68,0.4)' : 'rgba(204,95,95,0.4)';

    let progress = 0;
    const target = score;
    const step = () => {
      if (progress >= target) return;
      progress = Math.min(target, progress + 0.02);

      ctx.clearRect(0, 0, size, size);
      // track
      ctx.beginPath();
      ctx.arc(cx, cy, r, startAngle, startAngle + totalAngle);
      ctx.strokeStyle = '#312d29';
      ctx.lineWidth = lw;
      ctx.lineCap = 'butt';
      ctx.stroke();

      // arc
      ctx.beginPath();
      ctx.arc(cx, cy, r, startAngle, startAngle + totalAngle * progress);
      ctx.strokeStyle = color;
      ctx.lineWidth = lw;
      ctx.lineCap = 'round';
      ctx.shadowColor = glow;
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // value text
      ctx.fillStyle = color;
      ctx.font = `bold ${size * 0.22}px 'Space Mono', monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(Math.round(progress * 100).toString(), cx, cy - 4);

      // label
      if (label) {
        ctx.fillStyle = '#8a7a6f';
        ctx.font = `${size * 0.08}px 'Silkscreen', monospace`;
        ctx.fillText(label.toUpperCase(), cx, cy + size * 0.16);
      }

      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [score, size, label]);

  return <canvas ref={canvasRef} />;
}
