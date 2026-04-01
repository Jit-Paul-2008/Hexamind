"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float, PresentationControls, MeshTransmissionMaterial } from "@react-three/drei";
import { useRef } from "react";
import * as THREE from "three";

function GeometricalObject() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.2;
      meshRef.current.rotation.y += delta * 0.3;
    }
  });

  return (
    <Float speed={2} rotationIntensity={1.5} floatIntensity={2}>
      <mesh ref={meshRef} castShadow receiveShadow>
        <octahedronGeometry args={[2.5, 0]} />
        {/* A premium glass-like material to catch reflections */}
        <MeshTransmissionMaterial 
          backside 
          backsideThickness={2} 
          thickness={1} 
          roughness={0.05} 
          transmission={1} 
          ior={1.2} 
          chromaticAberration={0.05} 
          anisotropy={0.1}
          color="#b6bac5"
        />
      </mesh>
      {/* Inner object for structural depth */}
      <mesh scale={0.8}>
        <icosahedronGeometry args={[1.5, 1]} />
        <meshStandardMaterial color="#383e4e" wireframe />
      </mesh>
    </Float>
  );
}

export default function Scene() {
  return (
    <div className="absolute inset-0 z-0 bg-background overflow-hidden pointer-events-auto">
      <Canvas shadows camera={{ position: [0, 0, 7], fov: 45 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow color="#ffffff" />
        <directionalLight position={[-10, -10, -5]} intensity={2} color="#383e4e" />
        
        <PresentationControls
          global
          rotation={[0, 0, 0]}
          polar={[-Math.PI / 4, Math.PI / 4]}
          azimuth={[-Math.PI / 4, Math.PI / 4]}
        >
          <GeometricalObject />
        </PresentationControls>

        {/* The environment maps light perfectly on the glass surface */}
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
