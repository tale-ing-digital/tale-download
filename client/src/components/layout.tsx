import * as React from "react"
import { cn } from "@/lib/utils"

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background font-sans text-foreground selection:bg-primary/20 selection:text-primary">
      {/* Header Sobrio */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur-md transition-all">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Logo Placeholder - TALE Style */}
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-primary rounded-sm flex items-center justify-center text-white font-bold text-lg">
                T
              </div>
              <span className="text-lg font-bold tracking-tight text-foreground">
                TALE <span className="font-light text-muted-foreground">Download</span>
              </span>
            </div>
          </div>
          
          {/* User / Actions Placeholder */}
          <div className="flex items-center gap-4">
            <div className="h-8 w-8 rounded-full bg-secondary border border-input flex items-center justify-center text-xs font-medium text-muted-foreground">
              US
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 container py-8 md:py-12 animate-in fade-in duration-500 slide-in-from-bottom-4">
        {children}
      </main>

      {/* Footer Minimalista */}
      <footer className="border-t bg-muted/30 py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-xs text-muted-foreground text-center md:text-left">
            &copy; {new Date().getFullYear()} TALE Inmobiliaria. Uso interno exclusivo.
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>v1.0.0</span>
            <span className="h-3 w-[1px] bg-border" />
            <span>Soporte TI</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
