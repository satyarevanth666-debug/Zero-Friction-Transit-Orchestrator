"use client";

import Link from "next/link";
import { useState } from "react";
import { Compass, Menu, X, Database, Bookmark, LogIn } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-md bg-white/95 border-b border-slate-200/80 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Brand / Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform duration-200 relative">
            {/* Concentric location radar logo */}
            <div className="w-6 h-6 rounded-full border-2 border-white/60 flex items-center justify-center">
              <div className="w-2.5 h-2.5 rounded-full bg-white shadow-xs"></div>
            </div>
            <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white"></div>
          </div>
          <div className="flex flex-col">
            <div className="flex items-baseline">
              <span className="font-extrabold text-lg tracking-tight text-blue-600">Zero</span>
              <span className="font-extrabold text-lg tracking-tight text-slate-900">Friction</span>
            </div>
            <span className="text-[10px] font-medium text-slate-500 -mt-1 tracking-tight">
              Plan. Travel. Reach. Effortlessly.
            </span>
          </div>
        </Link>

        {/* Desktop Nav Links (Centered Pill Navigation) */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-medium">
          <Link
            href="/"
            className="px-4 py-1.5 rounded-full bg-blue-50 text-blue-600 font-semibold transition-colors"
          >
            Home
          </Link>
          <Link
            href="#plan-section"
            className="px-4 py-1.5 rounded-full text-slate-600 hover:text-slate-900 transition-colors"
          >
            Plan Journey
          </Link>
          <Link
            href="#how-it-works"
            className="px-4 py-1.5 rounded-full text-slate-600 hover:text-slate-900 transition-colors"
          >
            How it Works
          </Link>
          <Link
            href="#verified-routes"
            className="px-4 py-1.5 rounded-full text-slate-600 hover:text-slate-900 transition-colors"
          >
            Data & Truth Badges
          </Link>
        </nav>

        {/* Right Actions */}
        <div className="hidden md:flex items-center gap-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80 text-xs font-semibold shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>RAPTOR Live</span>
          </div>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-full border border-slate-300 hover:border-slate-400 text-slate-800 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <LogIn className="w-3.5 h-3.5 text-slate-600" />
            <span>Sign In</span>
          </Link>
        </div>

        {/* Mobile menu button */}
        <div className="flex md:hidden items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80 text-[11px] font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Live</span>
          </div>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-surface px-4 pt-2 pb-4 space-y-3">
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-xl text-sm font-medium hover:bg-surface-2"
          >
            Plan
          </Link>
          <Link
            href="/saved"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-xl text-sm font-medium hover:bg-surface-2 text-muted"
          >
            Saved Trips
          </Link>
          <Link
            href="/data-sources"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-xl text-sm font-medium hover:bg-surface-2 text-muted"
          >
            Data Sources & Truth Badges
          </Link>
          <Link
            href="/login"
            onClick={() => setMobileMenuOpen(false)}
            className="block w-full text-center px-4 py-2 text-sm font-semibold rounded-xl bg-brand-primary text-white"
          >
            Log in / Register
          </Link>
        </div>
      )}
    </header>
  );
}
