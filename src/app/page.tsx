"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen w-full overflow-hidden flex items-center justify-center bg-background">
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <Image 
          src="/images/flow-bg.png" 
          alt="Abstract Flow Background" 
          fill 
          priority
          className="object-cover opacity-80"
        />
        {/* Deep blur overlay to blend the edges and add depth */}
        <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/40 to-background/10 backdrop-blur-[2px]"></div>
      </div>

      {/* Glassmorphic Welcome Module */}
      <motion.div 
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 1, delay: 0.5, ease: "easeOut" }}
        className="relative z-10 p-10 md:p-16 rounded-[2rem] bg-indigo-charcoal/20 backdrop-blur-3xl border border-white/10 shadow-2xl flex flex-col items-center max-w-2xl text-center"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="w-16 h-16 rounded-full bg-white/10 mb-8 flex items-center justify-center border border-white/20 shadow-inner"
        >
          <div className="w-8 h-8 rounded-full bg-lavender-gray animate-pulse" />
        </motion.div>
        
        <h1 className="text-4xl md:text-5xl font-serif text-white tracking-tight leading-tight mb-4 drop-shadow-md">
          Welcome to <span className="text-lavender-gray italic font-light drop-shadow-lg">Hexamind</span>
        </h1>
        
        <p className="text-lg text-lavender-gray/80 font-sans font-light leading-relaxed mb-10 max-w-md mx-auto">
          Experience the intersection of analytical rigour and infinite exploration. Dive into our dual-agent cognitive environment.
        </p>

        {/* Action Button */}
        <Link href="/aria" className="group relative inline-flex items-center justify-center">
          <div className="absolute inset-0 bg-white/20 blur-xl rounded-full group-hover:bg-white/30 transition-all duration-500 opacity-0 group-hover:opacity-100"></div>
          <div className="px-8 py-4 rounded-full bg-white/10 backdrop-blur-md border border-white/20 group-hover:border-white/40 group-hover:bg-white/20 transition-all duration-300 relative z-10 flex items-center space-x-3">
            <span className="font-sans font-medium text-white tracking-widest uppercase text-sm">Initiate ARIA</span>
            <div className="w-4 h-[1px] bg-white group-hover:w-6 transition-all duration-300" />
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="transform group-hover:translate-x-1 transition-transform duration-300">
              <path d="M1 6H11M11 6L6 1M11 6L6 11" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </Link>
      </motion.div>
    </main>
  );
}
