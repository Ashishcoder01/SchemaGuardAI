import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: false,
        antialias: true,
        powerPreference: "low-power",
      });
    } catch {
      canvas.style.background =
        "radial-gradient(ellipse at 75% 45%, #20205d 0%, #090b19 48%, #050711 100%)";
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.65));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#050711");
    scene.fog = new THREE.FogExp2("#050711", 0.035);

    const camera = new THREE.PerspectiveCamera(
      48,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.set(0, 0, 13);

    const root = new THREE.Group();
    root.position.set(3.0, 0.0, -1.2);
    scene.add(root);

    // The central sculpture is a twisted, iridescent energy filament.
    const knotGeometry = new THREE.TorusKnotGeometry(2.35, 0.47, 260, 18, 2, 5);
    const knotMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColorA: { value: new THREE.Color("#25dcff") },
        uColorB: { value: new THREE.Color("#9a56ff") },
        uColorC: { value: new THREE.Color("#ff4dc8") },
      },
      vertexShader: `
        uniform float uTime;
        varying vec3 vNormal;
        varying vec3 vPosition;
        varying vec3 vWorld;
        varying float vWave;
        void main() {
          vec3 p = position;
          float wave = sin(position.x * 3.0 + uTime * 1.2)
                     * cos(position.y * 2.4 - uTime * 0.85);
          p += normal * wave * 0.055;
          vWave = wave;
          vNormal = normalize(normalMatrix * normal);
          vPosition = p;
          vec4 worldPosition = modelMatrix * vec4(p, 1.0);
          vWorld = worldPosition.xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColorA;
        uniform vec3 uColorB;
        uniform vec3 uColorC;
        varying vec3 vNormal;
        varying vec3 vPosition;
        varying vec3 vWorld;
        varying float vWave;
        void main() {
          vec3 viewDir = normalize(cameraPosition - vWorld);
          float fresnel = pow(1.0 - abs(dot(normalize(vNormal), viewDir)), 2.2);
          float bands = 0.5 + 0.5 * sin(
            vPosition.x * 5.0 + vPosition.y * 3.0
            + vPosition.z * 4.0 - uTime * 1.7
          );
          vec3 base = mix(uColorA, uColorB, bands);
          base = mix(base, uColorC, smoothstep(0.55, 1.0, bands + vWave * 0.25));
          vec3 color = base * (0.28 + bands * 0.28);
          color += uColorA * fresnel * 1.6;
          color += uColorB * pow(fresnel, 3.0) * 1.4;
          gl_FragColor = vec4(color, 0.91);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
      transparent: true,
      side: THREE.DoubleSide,
    });

    const knot = new THREE.Mesh(knotGeometry, knotMaterial);
    root.add(knot);

    // Thin orbital paths create a dynamic, engineered silhouette.
    const orbitMaterials = [
      new THREE.MeshBasicMaterial({
        color: "#39dfff",
        transparent: true,
        opacity: 0.62,
        blending: THREE.AdditiveBlending,
      }),
      new THREE.MeshBasicMaterial({
        color: "#a36aff",
        transparent: true,
        opacity: 0.54,
        blending: THREE.AdditiveBlending,
      }),
      new THREE.MeshBasicMaterial({
        color: "#ff5bd4",
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending,
      }),
    ];

    const orbits: THREE.Mesh[] = [];
    for (let i = 0; i < 5; i++) {
      const curve = new THREE.EllipseCurve(
        0, 0,
        3.1 + (i % 3) * 0.48,
        1.25 + (i % 2) * 0.65,
        0, Math.PI * 2,
        false,
        i * 0.3
      );
      const points = curve.getPoints(220).map((p) =>
        new THREE.Vector3(p.x, p.y, Math.sin(p.x * 0.6 + i) * 0.7)
      );
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const orbit = new THREE.Mesh(geometry, orbitMaterials[i % orbitMaterials.length]);
      orbit.rotation.set(i * 0.47, i * 0.28, i * 0.62);
      orbit.scale.setScalar(0.88 + i * 0.075);
      root.add(orbit);
      orbits.push(orbit);
    }

    // Fine luminous filaments: many flowing curves, not a connected-dot network.
    const filamentGroup = new THREE.Group();
    root.add(filamentGroup);

    const filamentMaterials = [
      new THREE.LineBasicMaterial({
        color: "#31dfff",
        transparent: true,
        opacity: 0.22,
        blending: THREE.AdditiveBlending,
      }),
      new THREE.LineBasicMaterial({
        color: "#9c6cff",
        transparent: true,
        opacity: 0.2,
        blending: THREE.AdditiveBlending,
      }),
    ];

    for (let j = 0; j < 34; j++) {
      const pts: THREE.Vector3[] = [];
      const phase = j * 0.42;
      for (let i = 0; i <= 90; i++) {
        const t = i / 90;
        const angle = t * Math.PI * 2 + phase;
        const radius = 2.6 + 0.38 * Math.sin(t * 18 + phase);
        pts.push(
          new THREE.Vector3(
            Math.cos(angle) * radius,
            Math.sin(angle * 1.7 + phase) * 1.5,
            Math.sin(angle + phase) * 1.2
          )
        );
      }
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        filamentMaterials[j % filamentMaterials.length]
      );
      filamentGroup.add(line);
    }

    // A deep field of tiny points drifts through the scene.
    const particleCount = window.innerWidth < 700 ? 800 : 1800;
    const positions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);
    const particleSpeeds = new Float32Array(particleCount);

    const cyan = new THREE.Color("#51e7ff");
    const violet = new THREE.Color("#a783ff");
    const pink = new THREE.Color("#ff6cdb");

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 32;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 22 - 3;
      const color = i % 7 === 0 ? pink : i % 2 === 0 ? cyan : violet;
      particleColors[i * 3] = color.r;
      particleColors[i * 3 + 1] = color.g;
      particleColors[i * 3 + 2] = color.b;
      particleSpeeds[i] = 0.15 + Math.random() * 0.7;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(positions, 3)
    );
    particleGeometry.setAttribute(
      "color",
      new THREE.BufferAttribute(particleColors, 3)
    );

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.035,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    // A soft atmospheric halo sits behind the 3D sculpture.
    const haloGeometry = new THREE.PlaneGeometry(15, 15);
    const haloMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        varying vec2 vUv;
        void main() {
          vec2 p = vUv - 0.5;
          p.x *= 0.82;
          float d = length(p);
          float cloud = 0.5 + 0.5 * sin(atan(p.y, p.x) * 5.0 + uTime * 0.3);
          float halo = exp(-d * 5.0) * (0.5 + cloud * 0.5);
          vec3 color = mix(vec3(0.08, 0.13, 0.65), vec3(0.02, 0.72, 0.95), cloud);
          gl_FragColor = vec4(color, halo * 0.28);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    });
    const halo = new THREE.Mesh(haloGeometry, haloMaterial);
    halo.position.set(0, 0, -3.8);
    root.add(halo);

    const clock = new THREE.Clock();
    let raf = 0;
    let targetX = 0;
    let targetY = 0;

    function onPointerMove(event: PointerEvent) {
      targetX = (event.clientX / window.innerWidth - 0.5) * 0.45;
      targetY = (event.clientY / window.innerHeight - 0.5) * 0.28;
    }

    let width = window.innerWidth;
    let height = window.innerHeight;

    function onResize() {
      width = window.innerWidth;
      height = window.innerHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.65));
      renderer.setSize(width, height);
    }

    let visible = !document.hidden;

    function onVisibilityChange() {
      visible = !document.hidden;
      if (visible && !reducedMotion.matches) {
        clock.start();
        raf = requestAnimationFrame(animate);
      }
    }

    function animate() {
      if (!visible) return;

      const delta = Math.min(clock.getDelta(), 0.04);
      const elapsed = clock.elapsedTime;

      if (!reducedMotion.matches) {
        knotMaterial.uniforms.uTime.value = elapsed;
        haloMaterial.uniforms.uTime.value = elapsed;
        root.rotation.y += delta * 0.075;
        root.rotation.x = Math.sin(elapsed * 0.16) * 0.09;
        root.rotation.z = Math.sin(elapsed * 0.12) * 0.07;

        orbits.forEach((orbit, i) => {
          orbit.rotation.z += delta * (i % 2 ? -0.09 : 0.065);
          orbit.rotation.x += delta * (i % 2 ? 0.035 : -0.025);
        });

        filamentGroup.rotation.y -= delta * 0.035;
        filamentGroup.rotation.x = Math.sin(elapsed * 0.18) * 0.12;

        const pos = particleGeometry.attributes.position as THREE.BufferAttribute;
        for (let i = 0; i < particleCount; i++) {
          let z = pos.getZ(i) + delta * particleSpeeds[i] * 0.6;
          if (z > 8) z = -18;
          pos.setZ(i, z);
        }
        pos.needsUpdate = true;
      }

      camera.position.x += (targetX - camera.position.x) * 0.025;
      camera.position.y += (-targetY - camera.position.y) * 0.025;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);

      if (!reducedMotion.matches) raf = requestAnimationFrame(animate);
    }

    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onPointerMove);
    document.addEventListener("visibilitychange", onVisibilityChange);

    if (reducedMotion.matches) {
      renderer.render(scene, camera);
    } else {
      animate();
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("visibilitychange", onVisibilityChange);

      knotGeometry.dispose();
      knotMaterial.dispose();
      orbitMaterials.forEach((material) => material.dispose());
      orbits.forEach((orbit) => orbit.geometry.dispose());
      filamentMaterials.forEach((material) => material.dispose());
      filamentGroup.children.forEach((child) => {
        if (child instanceof THREE.Line) child.geometry.dispose();
      });
      particleGeometry.dispose();
      particleMaterial.dispose();
      haloGeometry.dispose();
      haloMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="animated-network-background"
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        display: "block",
        pointerEvents: "none",
        zIndex: 0,
      }}
    />
  );
}
