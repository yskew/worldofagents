import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function GlobeCanvas({ size = 300 }: { size?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current!;
    const PIXEL = 96;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.z = 3.6;

    // render at tiny resolution
    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
    renderer.setSize(PIXEL, PIXEL);
    renderer.setPixelRatio(1);

    // upscale canvas with pixelated rendering
    const canvas = renderer.domElement;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    canvas.style.imageRendering = 'pixelated';
    el.appendChild(canvas);

    const coral = 0xd97757;
    const peach = 0xe89b7d;
    const dim = 0x5e524a;

    const icoGeo = new THREE.IcosahedronGeometry(1.0, 2);
    const icoMat = new THREE.MeshBasicMaterial({ color: coral, wireframe: true, transparent: true, opacity: 0.3 });
    const ico = new THREE.Mesh(icoGeo, icoMat);
    scene.add(ico);

    const innerGeo = new THREE.IcosahedronGeometry(0.85, 1);
    const innerMat = new THREE.PointsMaterial({ color: peach, size: 0.06, transparent: true, opacity: 0.8 });
    scene.add(new THREE.Points(innerGeo, innerMat));

    for (let i = 0; i < 3; i++) {
      const r = 1.25 + i * 0.18;
      const ringGeo = new THREE.RingGeometry(r, r + 0.012, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: dim, transparent: true, opacity: 0.15 - i * 0.04, side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2 + (i - 1) * 0.35;
      ring.rotation.z = i * 0.25;
      scene.add(ring);
    }

    const pCount = 40;
    const pGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(pCount * 3);
    for (let i = 0; i < pCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 1.4 + Math.random() * 0.7;
      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = radius * Math.cos(phi);
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pMat = new THREE.PointsMaterial({ color: coral, size: 0.04, transparent: true, opacity: 0.5 });
    const pts = new THREE.Points(pGeo, pMat);
    scene.add(pts);

    let raf: number;
    const animate = () => {
      const t = performance.now() * 0.001;
      ico.rotation.y = t * 0.15;
      ico.rotation.x = Math.sin(t * 0.08) * 0.12;
      pts.rotation.y = -t * 0.06;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      if (el.contains(canvas)) el.removeChild(canvas);
      renderer.dispose();
    };
  }, [size]);

  return <div ref={ref} style={{ width: size, height: size, lineHeight: 0 }} />;
}
