import Link from "next/link";
import { ShieldCheck, Twitter, Instagram, Youtube } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-slate-200/80 bg-white mt-auto py-10 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <div className="w-5 h-5 rounded-full border-2 border-white/60 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white"></div>
              </div>
            </div>
            <div className="flex flex-col">
              <div className="flex items-baseline">
                <span className="font-extrabold text-base tracking-tight text-blue-600">Zero</span>
                <span className="font-extrabold text-base tracking-tight text-slate-900">Friction</span>
              </div>
              <span className="text-[10px] font-medium text-slate-500 -mt-1 tracking-tight">
                Plan. Travel. Reach. Effortlessly.
              </span>
            </div>
          </Link>

          {/* Links */}
          <div className="flex items-center gap-6 text-xs font-medium text-slate-600">
            <Link href="#about" className="hover:text-blue-600 transition-colors">
              About
            </Link>
            <Link href="#privacy" className="hover:text-blue-600 transition-colors">
              Privacy
            </Link>
            <Link href="#terms" className="hover:text-blue-600 transition-colors">
              Terms
            </Link>
            <Link href="#help" className="hover:text-blue-600 transition-colors">
              Help
            </Link>
          </div>

          {/* Social Icons */}
          <div className="flex items-center gap-4 text-slate-500">
            <a href="https://twitter.com" target="_blank" rel="noreferrer" className="hover:text-blue-600 transition-colors">
              <Twitter className="w-4 h-4" />
            </a>
            <a href="https://instagram.com" target="_blank" rel="noreferrer" className="hover:text-pink-600 transition-colors">
              <Instagram className="w-4 h-4" />
            </a>
            <a href="https://youtube.com" target="_blank" rel="noreferrer" className="hover:text-red-600 transition-colors">
              <Youtube className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Data transparency note */}
        <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Source labels are shown where available · Unknown fares are not treated as zero</span>
          </div>
          <div className="text-slate-400">
            &copy; 2026 ZeroFriction Transit. All rights reserved.
          </div>
        </div>
      </div>
    </footer>
  );
}
