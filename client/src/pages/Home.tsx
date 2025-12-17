import { useState } from "react"
import { Layout } from "@/components/layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Icons, iconStyle } from "@/lib/icons"

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)

  // Simulación de carga inicial
  useState(() => {
    setIsLoading(true)
    const timer = setTimeout(() => setIsLoading(false), 800)
    return () => clearTimeout(timer)
  })

  return (
    <Layout>
      {/* Hero Section Minimalista */}
      <section className="mb-12 space-y-4 text-center md:text-left max-w-3xl mx-auto md:mx-0">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Centro de Documentos
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Accede, consulta y descarga la documentación técnica de tus proyectos de forma centralizada y segura.
        </p>
      </section>

      {/* Search & Filter Bar */}
      <section className="mb-8 sticky top-20 z-40">
        <Card className="border-none shadow-lg bg-white/90 backdrop-blur-sm">
          <CardContent className="p-4 flex flex-col md:flex-row gap-4 items-center">
            <div className="relative flex-1 w-full">
              <Icons.search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input 
                placeholder="Buscar por código, nombre de proyecto o tipo..." 
                className="pl-10 h-12 text-base border-transparent bg-secondary/50 focus:bg-white transition-all"
              />
            </div>
            <div className="flex gap-2 w-full md:w-auto">
              <Button variant="outline" className="flex-1 md:flex-none gap-2 h-12 border-dashed">
                <Icons.filter {...iconStyle} />
                Filtros
              </Button>
              <Button variant="talePrimary" className="flex-1 md:flex-none h-12 px-8 shadow-md shadow-primary/20">
                Buscar
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Results Grid */}
      <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          // Loading Skeletons
          Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="border-none shadow-sm bg-muted/20">
              <CardHeader className="pb-4">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full rounded-md" />
              </CardContent>
            </Card>
          ))
        ) : (
          // Document Cards
          <>
            <DocumentCard 
              title="Planos Estructurales - Torre A"
              project="Residencial Miraflores"
              type="PDF"
              size="24 MB"
              date="17 Dic 2025"
              status="approved"
            />
            <DocumentCard 
              title="Memoria Descriptiva v2.0"
              project="Oficinas San Isidro"
              type="DOCX"
              size="1.2 MB"
              date="16 Dic 2025"
              status="review"
            />
            <DocumentCard 
              title="Levantamiento Topográfico"
              project="Lote 45 - Surco"
              type="DWG"
              size="156 MB"
              date="15 Dic 2025"
              status="approved"
            />
             <DocumentCard 
              title="Presupuesto General"
              project="Residencial Miraflores"
              type="XLSX"
              size="4.5 MB"
              date="14 Dic 2025"
              status="pending"
            />
             <DocumentCard 
              title="Render Fachada Principal"
              project="Oficinas San Isidro"
              type="JPG"
              size="12 MB"
              date="12 Dic 2025"
              status="approved"
            />
             <DocumentCard 
              title="Licencia de Construcción"
              project="Lote 45 - Surco"
              type="PDF"
              size="8.1 MB"
              date="10 Dic 2025"
              status="approved"
            />
          </>
        )}
      </section>
    </Layout>
  )
}

function DocumentCard({ title, project, type, size, date, status }: any) {
  return (
    <Card className="group hover:border-primary/50 hover:shadow-md transition-all duration-300 cursor-pointer overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-2">
          <Badge variant="outline" className="font-normal text-muted-foreground bg-secondary/50 border-transparent">
            {project}
          </Badge>
          <StatusBadge status={status} />
        </div>
        <CardTitle className="text-lg mt-2 group-hover:text-primary transition-colors line-clamp-1">
          {title}
        </CardTitle>
        <CardDescription className="flex items-center gap-2 text-xs">
          <span>{date}</span>
          <span className="h-1 w-1 rounded-full bg-muted-foreground/30" />
          <span>{size}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-24 rounded-md bg-secondary/30 border border-dashed border-secondary flex items-center justify-center group-hover:bg-primary/5 group-hover:border-primary/20 transition-all">
          <div className="flex flex-col items-center gap-1 text-muted-foreground group-hover:text-primary/80">
            <Icons.file className="h-8 w-8" strokeWidth={1} />
            <span className="text-xs font-medium">{type}</span>
          </div>
        </div>
        <div className="mt-4 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity transform translate-y-2 group-hover:translate-y-0 duration-200">
          <Button size="sm" variant="taleSecondary" className="h-8 text-xs gap-1">
            <Icons.download className="h-3 w-3" />
            Descargar
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles = {
    approved: "bg-emerald-50 text-emerald-700 border-emerald-100",
    review: "bg-amber-50 text-amber-700 border-amber-100",
    pending: "bg-slate-50 text-slate-600 border-slate-100"
  }
  
  const labels = {
    approved: "Aprobado",
    review: "En Revisión",
    pending: "Pendiente"
  }

  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${styles[status as keyof typeof styles]}`}>
      {labels[status as keyof typeof labels]}
    </span>
  )
}
