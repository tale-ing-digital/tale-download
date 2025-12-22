import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Layout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { SearchIcon, DownloadIcon, FileTextIcon, CalendarIcon } from '@/lib/icons';
import {
  getProjectsList,
  getDocuments,
  downloadProjectZip,
  handleApiError,
  type Document,
  type Project,
} from '@/lib/api';

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [documentTypeOptions, setDocumentTypeOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  // Estado para mostrar documentos de un proyecto específico
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [projectDocuments, setProjectDocuments] = useState<Record<string, Document[]>>({});
  const [loadingDocs, setLoadingDocs] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const projectsData = await getProjectsList();
      setProjects(projectsData.projects);
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadProjectZip = async (projectCode: string) => {
    setDownloading(projectCode);
    const toastId = toast.loading(`Generando ZIP del proyecto ${projectCode}...`);
    try {
      await downloadProjectZip(projectCode);
      toast.success(`ZIP del proyecto ${projectCode} descargado exitosamente`, { id: toastId });
    } catch (error) {
      toast.error(handleApiError(error), { id: toastId });
    } finally {
      setDownloading(null);
    }
  };

  const handleExpandProject = async (projectCode: string) => {
    if (expandedProject === projectCode) {
      setExpandedProject(null);
    } else {
      setExpandedProject(projectCode);
      
      // Cargar documentos si no están cacheados
      if (!projectDocuments[projectCode]) {
        setLoadingDocs(projectCode);
        try {
          const response = await getDocuments({
            project_code: projectCode,
            limit: 100,
            offset: 0,
          });
          setProjectDocuments(prev => ({
            ...prev,
            [projectCode]: response.documents,
          }));
        } catch (error) {
          toast.error(handleApiError(error));
        } finally {
          setLoadingDocs(null);
        }
      }
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-background">
        <section className="py-16 px-4">
          <div className="container max-w-7xl">
            {/* HEADER */}
            <div className="text-center mb-12">
              <h1 className="text-4xl font-bold text-foreground mb-4">
                Exportación Documental
              </h1>
              <p className="text-lg text-muted-foreground">
                Descarga documentos de tus proyectos en ZIP
              </p>
            </div>

            {/* GRID DE PROYECTOS */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Card key={i}>
                    <CardHeader>
                      <Skeleton className="h-6 w-3/4" />
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-2/3" />
                      <Skeleton className="h-10 w-full mt-4" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <>
                <div className="mb-6 flex items-center justify-between">
                  <h2 className="text-2xl font-semibold text-foreground">Proyectos ({projects.length})</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {projects.map((project) => {
                    const isExpanded = expandedProject === project.codigo_proyecto;
                    const docs = projectDocuments[project.codigo_proyecto] || [];
                    const isLoadingThisProject = loadingDocs === project.codigo_proyecto;

                    return (
                      <Card
                        key={project.codigo_proyecto}
                        className="flex flex-col hover:shadow-md transition-all duration-200"
                      >
                        <CardHeader>
                          <div className="space-y-2">
                            <CardTitle className="text-base">
                              <div className="text-xs font-normal text-muted-foreground mb-1">
                                {project.codigo_proyecto}
                              </div>
                              <div className="font-bold text-foreground">
                                {project.nombre_proyecto}
                              </div>
                            </CardTitle>
                          </div>
                        </CardHeader>

                        <CardContent className="flex-1 space-y-4">
                          {/* RESUMEN */}
                          <div className="space-y-2 p-3 rounded bg-muted/30">
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-muted-foreground">Documentos</span>
                              <Badge variant="tale">{project.total_documentos || 0}</Badge>
                            </div>
                            {project.ultima_fecha_carga && (
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <CalendarIcon className="w-3 h-3" />
                                <span>{new Date(project.ultima_fecha_carga).toLocaleDateString('es-ES')}</span>
                              </div>
                            )}
                          </div>

                          {/* BOTONES */}
                          <div className="flex flex-col gap-2 pt-2">
                            <Button
                              onClick={() => handleDownloadProjectZip(project.codigo_proyecto)}
                              variant="talePrimary"
                              size="sm"
                              className="w-full"
                              disabled={downloading === project.codigo_proyecto}
                            >
                              <DownloadIcon className="mr-2 w-4 h-4" />
                              {downloading === project.codigo_proyecto ? 'Descargando...' : 'Descargar ZIP'}
                            </Button>

                            <Button
                              onClick={() => handleExpandProject(project.codigo_proyecto)}
                              variant="taleSecondary"
                              size="sm"
                              className="w-full"
                            >
                              <FileTextIcon className="mr-2 w-4 h-4" />
                              {isExpanded ? 'Ocultar' : 'Ver'} documentos
                            </Button>
                          </div>

                          {/* LISTA DE DOCUMENTOS (EXPANDIBLE) */}
                          {isExpanded && (
                            <div className="space-y-2 border-t pt-4">
                              {isLoadingThisProject ? (
                                <div className="space-y-2">
                                  {[1, 2, 3].map((i) => (
                                    <Skeleton key={i} className="h-12" />
                                  ))}
                                </div>
                              ) : docs.length === 0 ? (
                                <p className="text-xs text-muted-foreground text-center py-2">
                                  No hay documentos
                                </p>
                              ) : (
                                <div className="space-y-1 max-h-64 overflow-y-auto">
                                  {docs.slice(0, 10).map((doc, idx) => (
                                    <div
                                      key={idx}
                                      className="p-2 rounded bg-background border border-border/30 text-xs"
                                    >
                                      <div className="font-medium truncate text-foreground">
                                        {doc.nombre_archivo}
                                      </div>
                                      <div className="text-muted-foreground">
                                        {doc.codigo_unidad}
                                      </div>
                                      <div className="flex justify-between items-center mt-1">
                                        <span className="text-muted-foreground">
                                          {new Date(doc.fecha_carga).toLocaleDateString('es-ES')}
                                        </span>
                                        <Badge variant="outline" className="text-xs py-0">
                                          {doc.tipo_documento}
                                        </Badge>
                                      </div>
                                    </div>
                                  ))}
                                  {docs.length > 10 && (
                                    <p className="text-xs text-muted-foreground text-center py-2">
                                      +{docs.length - 10} documentos más
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {projects.length === 0 && (
                  <Card className="text-center py-12">
                    <CardContent>
                      <FileTextIcon className="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
                      <p className="text-muted-foreground">
                        No hay proyectos disponibles
                      </p>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </section>
      </div>
    </Layout>
  );
}
