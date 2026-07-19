import { Globe } from "@/components/Globe"
import { Button } from "@/components/ui/button"

function App() {
  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Hack-nation for India
          </h1>
          <p className="text-sm text-muted-foreground">
            Vite + React + TS · shadcn/ui · react-globe.gl
          </p>
        </div>
        <Button size="sm">Get started</Button>
      </header>

      <main className="relative flex-1 overflow-hidden bg-black">
        <Globe />
        <div className="pointer-events-none absolute bottom-6 left-6 max-w-xs rounded-lg border border-white/10 bg-black/40 p-4 text-white backdrop-blur">
          <p className="text-sm font-medium">Interactive globe</p>
          <p className="mt-1 text-xs text-white/70">
            Drag to rotate · scroll to zoom · hover a point for its city.
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
