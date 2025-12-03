"use client";
import { useEffect, useRef, useState } from "react";
import { createNoise3D } from "simplex-noise";
import { motion } from "motion/react";
import clsx from "clsx";

interface VortexProps {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  particleCount?: number;
  rangeY?: number;
  baseHue?: number;
  baseSpeed?: number;
  rangeSpeed?: number;
  baseRadius?: number;
  rangeRadius?: number;
  backgroundColor?: string;
}

export function Vortex({
  children,
  className,
  containerClassName,
  particleCount = 700,
  rangeY = 100,
  baseHue = 220,
  baseSpeed = 0.0,
  rangeSpeed = 1.5,
  baseRadius = 1,
  rangeRadius = 2,
  backgroundColor = "#000000",
}: VortexProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  useEffect(() => {
    if (!canvasRef.current || dimensions.width === 0 || dimensions.height === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const noise3D = createNoise3D();
    let animationFrameId: number;
    let tick = 0;

    const { width, height } = dimensions;
    const centerX = width / 2;
    const centerY = height / 2;

    // Particle class
    class Particle {
      x: number;
      y: number;
      originX: number;
      originY: number;
      hue: number;
      radius: number;
      speed: number;
      angle: number;
      noiseOffsetX: number;
      noiseOffsetY: number;

      constructor() {
        this.originX = Math.random() * width;
        this.originY = centerY + (Math.random() - 0.5) * rangeY * 2;
        this.x = this.originX;
        this.y = this.originY;
        this.hue = baseHue + Math.random() * 60 - 30;
        this.radius = baseRadius + Math.random() * rangeRadius;
        this.speed = baseSpeed + Math.random() * rangeSpeed;
        this.angle = Math.random() * Math.PI * 2;
        this.noiseOffsetX = Math.random() * 1000;
        this.noiseOffsetY = Math.random() * 1000;
      }

      update(t: number) {
        // Calculate noise-based movement (slower, more subtle)
        const noiseX = noise3D(this.noiseOffsetX, t * 0.00015, 0) * 1.5;
        const noiseY = noise3D(this.noiseOffsetY, t * 0.00015, 0) * 1.5;

        // Vortex effect - particles spiral gently
        const dx = this.x - centerX;
        const dy = this.y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = Math.max(width, height) / 2;

        // Gentle angular velocity
        const angularVelocity = (1 - distance / maxDistance) * 0.008 + 0.002;
        this.angle += angularVelocity * this.speed;

        // Subtle radial movement with noise
        const radialNoise = noise3D(this.x * 0.003, this.y * 0.003, t * 0.0001);
        const radialVelocity = radialNoise * 0.3;

        // Update position with gentle vortex motion
        this.x += Math.cos(this.angle) * this.speed * 0.5 + noiseX + radialVelocity * dx * 0.005;
        this.y += Math.sin(this.angle) * this.speed * 0.5 + noiseY + radialVelocity * dy * 0.005;

        // Wrap around edges
        if (this.x < -50) this.x = width + 50;
        if (this.x > width + 50) this.x = -50;
        if (this.y < -50) this.y = height + 50;
        if (this.y > height + 50) this.y = -50;
      }

      draw(ctx: CanvasRenderingContext2D) {
        const dx = this.x - centerX;
        const dy = this.y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = Math.max(width, height) / 2;

        // Subtle opacity based on distance from center
        const opacity = 0.15 + (1 - distance / maxDistance) * 0.35;

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${this.hue}, 70%, 55%, ${opacity})`;
        ctx.fill();
      }
    }

    // Initialize particles
    const particles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    // Animation loop
    const animate = () => {
      // Clear canvas properly - use clearRect for transparent backgrounds
      if (backgroundColor === "transparent") {
        ctx.clearRect(0, 0, width, height);
      } else {
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(0, 0, width, height);
      }

      // Draw connecting lines between nearby particles (very subtle)
      ctx.lineWidth = 0.3;

      for (let i = 0; i < particles.length; i += 3) { // Skip some particles for performance
        for (let j = i + 1; j < particles.length; j += 3) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 40) {
            const opacity = (1 - distance / 40) * 0.03;
            ctx.strokeStyle = `hsla(${baseHue}, 60%, 50%, ${opacity})`;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // Update and draw particles
      for (const particle of particles) {
        particle.update(tick);
        particle.draw(ctx);
      }

      tick++;
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [dimensions, particleCount, rangeY, baseHue, baseSpeed, rangeSpeed, baseRadius, rangeRadius, backgroundColor]);

  return (
    <div ref={containerRef} className={clsx("relative h-full w-full overflow-hidden", containerClassName)}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
        className="absolute inset-0"
      >
        <canvas
          ref={canvasRef}
          width={dimensions.width}
          height={dimensions.height}
          style={{
            width: "100%",
            height: "100%",
          }}
        />
      </motion.div>
      {children && (
        <div className={clsx("relative z-10", className)}>
          {children}
        </div>
      )}
    </div>
  );
}
