"use client";

import { motion } from "framer-motion";

const DUMMY_ITEMS = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  title: `Project // 00${i + 1}`,
  description: "Advanced AI computation simulation and continuous logic evolution parameters.",
}));

export default function OverlayList() {
  return (
    <div className="relative z-10 w-full h-screen pointer-events-none flex flex-col md:flex-row justify-between items-end p-6 md:p-12 lg:p-24 overflow-hidden">
      
      {/* Title block */}
      <motion.div
        initial={{ opacity: 0, y: 50, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-xl mb-12 md:mb-0 pointer-events-auto"
      >
        <h1 className="text-5xl md:text-7xl font-serif text-white tracking-tight leading-none mb-6 drop-shadow-2xl">
          Digital
          <br />
          <span className="text-lavender-gray italic font-serif">Brutalism</span>
        </h1>
        <p className="text-lg text-lavender-gray/90 max-w-md font-sans leading-relaxed tracking-wide">
          Navigating the intersection of high-fidelity aesthetics and ARIA-driven computational intelligence. 
          Experience real-time interactive paradigms.
        </p>
      </motion.div>

      {/* Infinite scrolling block (dummy) */}
      <div className="w-full md:w-[400px] h-[50vh] md:h-[70vh] pointer-events-none relative" style={{ maskImage: "linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)", WebkitMaskImage: "linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)" }}>
        <div className="h-full w-full flex flex-col gap-4 overflow-y-auto pointer-events-auto snap-y snap-mandatory pb-[30vh] pr-2 scrollbar-none" style={{ scrollbarWidth: "none" }}>
          {DUMMY_ITEMS.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 + i * 0.05, ease: "easeOut" }}
              className="bg-indigo-charcoal/20 backdrop-blur-2xl border border-white/5 p-6 rounded-3xl snap-start cursor-pointer hover:bg-white/10 hover:border-white/20 transition-all duration-300 group"
            >
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-sans font-medium text-white text-sm tracking-widest uppercase group-hover:text-lavender-gray transition-colors">
                  {item.title}
                </h3>
                <div className="h-2 w-2 rounded-full bg-lavender-gray/50 group-hover:bg-white transition-colors" />
              </div>
              <p className="font-sans text-sm text-lavender-gray/60 leading-relaxed font-light">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
      
    </div>
  );
}
