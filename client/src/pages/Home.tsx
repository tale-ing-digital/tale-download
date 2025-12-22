import { useState, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
import { Layout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DownloadIcon, FileTextIcon, CalendarIcon, SearchIcon, FilterIcon, XIcon, FileText2Icon, CheckCircleIcon, AlertIcon, ClipboardIcon, BellIcon, HelpCircleIcon } from '@/lib/icons';
import {
  getProjectsList,
  getDocuments,
  downloadProjectZip,
  handleApiError,
  type Document,
  type Project,
} from '@/lib/api';

interface FilterState {
  documentTypes: string[];
  startDate: string;
  endDate: string;
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // SEPARACIÓN: filtros en preparación vs filtros aplicados
  const [pendingFilters, setPendingFilters] = useState<FilterState>({
    documentTypes: [],
    startDate: '',
    endDate: '',
  });
  const [appliedFilters, setAppliedFilters] = useState<FilterState>({
    documentTypes: [],
    startDate: '',
    endDate: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  // Estado para mostrar documentos de un proyecto específico
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [projectDocuments, setProjectDocuments] = useState<Record<string, Document[]>>({});
  const [loadingDocs, setLoadingDocs] = useState<string | null>(null);

  // Filtrar proyectos según búsqueda
  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects;
    
    const query = searchQuery.toLowerCase();
    return projects.filter(p => 
      p.codigo_proyecto.toLowerCase().includes(query) ||
      p.nombre_proyecto.toLowerCase().includes(query)
    );
  }, [projects, searchQuery]);

  const hasActiveFilters = pendingFilters.documentTypes.length > 0 || pendingFilters.startDate || pendingFilters.endDate;
  const hasAppliedFilters = appliedFilters.documentTypes.length > 0 || appliedFilters.startDate || appliedFilters.endDate;

  const documentTypes = ['Voucher', 'Minuta', 'Adenda', 'Carta de Aprobación', 'Otro'];

  const getDocTypeIcon = (type: string) => {
    const iconProps = { className: 'w-4 h-4' };
    switch (type) {
      case 'Voucher':
        return <CheckCircleIcon {...iconProps} />;
      case 'Minuta':
        return <FileText2Icon {...iconProps} />;
      case 'Adenda':
        return <AlertIcon {...iconProps} />;
      case 'Carta de Aprobación':
        return <ClipboardIcon {...iconProps} />;
      default:
        return <HelpCircleIcon {...iconProps} />;
    }
  };

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
      // Construir query params CON los filtros APLICADOS
      const params = new URLSearchParams();
      
      if (appliedFilters.documentTypes.length > 0) {
        params.append('document_types', appliedFilters.documentTypes.join(','));
      }
      if (appliedFilters.startDate) {
        params.append('start_date', appliedFilters.startDate);
      }
      if (appliedFilters.endDate) {
        params.append('end_date', appliedFilters.endDate);
      }
      
      const queryString = params.toString();
      const url = queryString ? `?${queryString}` : '';
      
      await downloadProjectZip(projectCode, url);
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
      
      // Cargar documentos si no están cacheados, usando filtros APLICADOS
      if (!projectDocuments[projectCode]) {
        setLoadingDocs(projectCode);
        try {
          const response = await getDocuments({
            project_code: projectCode,
            limit: 10000,
            offset: 0,
            document_types: appliedFilters.documentTypes.length > 0 ? appliedFilters.documentTypes.join(',') : undefined,
            start_date: appliedFilters.startDate || undefined,
            end_date: appliedFilters.endDate || undefined,
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

  const handleApplyFilters = () => {
    // Aplicar filtros pendientes
    setAppliedFilters({ ...pendingFilters });
    
    // Limpiar caché de documentos para forzar recarga con nuevos filtros
    setProjectDocuments({});
    setExpandedProject(null);
    
    // Mensaje de confirmación
    const filterCount = pendingFilters.documentTypes.length + 
                        (pendingFilters.startDate ? 1 : 0) + 
                        (pendingFilters.endDate ? 1 : 0);
    toast.success(`${filterCount} filtro${filterCount !== 1 ? 's' : ''} aplicado${filterCount !== 1 ? 's' : ''}`);
  };

  const handleClearFilters = () => {
    // Limpiar tanto filtros pendientes como aplicados
    const emptyFilters = {
      documentTypes: [],
      startDate: '',
      endDate: '',
    };
    setPendingFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
    
    // Limpiar caché para forzar recarga sin filtros
    setProjectDocuments({});
    setExpandedProject(null);
    
    // Mensaje de confirmación
    toast.success('Filtros eliminados');
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

            {/* SEARCH */}
            <div className="mb-8">
              <div className="relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por código o nombre de proyecto..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 h-10"
                />
              </div>
              {searchQuery && (
                <p className="text-xs text-muted-foreground mt-2">
                  {filteredProjects.length} de {projects.length} proyectos
                </p>
              )}
            </div>

            {/* FILTERS PANEL */}
            <Card className="mb-8 border-border/50">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowFilters(!showFilters)}>
                  <div className="flex items-center gap-2">
                    <FilterIcon className="w-4 h-4" />
                    <CardTitle className="text-base">Filtros</CardTitle>
                    {hasAppliedFilters && (
                      <Badge variant="secondary" className="ml-2">
                        {appliedFilters.documentTypes.length + (appliedFilters.startDate ? 1 : 0) + (appliedFilters.endDate ? 1 : 0)}
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">{showFilters ? '−' : '+'}</span>
                </div>
              </CardHeader>

              {showFilters && (
                <CardContent className="space-y-4 border-t pt-4">
                  {/* DOCUMENT TYPES */}
                  <div>
                    <label className="text-sm font-medium text-foreground mb-2 block">Tipos de Documento</label>
                    <div className="grid grid-cols-2 gap-3">
                      {documentTypes.map((type) => (
                        <label key={type} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={pendingFilters.documentTypes.includes(type)}
                            onChange={(e) => {
                              setPendingFilters(prev => ({
                                ...prev,
                                documentTypes: e.target.checked
                                  ? [...prev.documentTypes, type]
                                  : prev.documentTypes.filter(t => t !== type),
                              }));
                            }}
                            className="w-4 h-4 rounded"
                          />
                          <span className="text-muted-foreground">
                            {getDocTypeIcon(type)}
                          </span>
                          <span className="text-sm text-foreground">{type}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* DATE RANGE */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-foreground mb-2 block">Desde</label>
                      <Input
                        type="date"
                        value={pendingFilters.startDate}
                        onChange={(e) => setPendingFilters(prev => ({ ...prev, startDate: e.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-foreground mb-2 block">Hasta</label>
                      <Input
                        type="date"
                        value={pendingFilters.endDate}
                        onChange={(e) => setPendingFilters(prev => ({ ...prev, endDate: e.target.value }))}
                      />
                    </div>
                  </div>

                  {/* BOTONES DE ACCIÓN */}
                  <div className="flex gap-2">
                    <Button
                      onClick={handleApplyFilters}
                      variant="default"
                      size="sm"
                      className="flex-1"
                      disabled={!hasActiveFilters}
                    >
                      <FilterIcon className="mr-2 w-4 h-4" />
                      Filtrar
                    </Button>
                    
                    {hasAppliedFilters && (
                      <Button
                        onClick={handleClearFilters}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        <XIcon className="mr-2 w-4 h-4" />
                        Quitar filtros
                      </Button>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>

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
                  {filteredProjects.map((project) => {
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
                              <Badge variant="secondary">
                                {expandedProject === project.codigo_proyecto && projectDocuments[project.codigo_proyecto]
                                  ? projectDocuments[project.codigo_proyecto].length
                                  : project.total_documentos || 0}
                              </Badge>
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
                              variant="default"
                              size="sm"
                              className="w-full"
                              disabled={downloading === project.codigo_proyecto}
                            >
                              <DownloadIcon className="mr-2 w-4 h-4" />
                              {downloading === project.codigo_proyecto ? 'Descargando...' : 'Descargar ZIP'}
                            </Button>

                            <Button
                              onClick={() => handleExpandProject(project.codigo_proyecto)}
                              variant="outline"
                              size="sm"
                              className="w-full"
                            >
                              <FileTextIcon className="mr-2 w-4 h-4" />
                              {isExpanded ? 'Ocultar' : 'Ver'} documentos
                            </Button>
                          </div>

                          {/* ESTADÍSTICAS (EXPANDIBLE) */}
                          {isExpanded && (
                            <div className="space-y-3 border-t pt-4">
                              {isLoadingThisProject ? (
                                <div className="space-y-2">
                                  {[1, 2, 3].map((i) => (
                                    <Skeleton key={i} className="h-10" />
                                  ))}
                                </div>
                              ) : docs.length === 0 ? (
                                <p className="text-xs text-muted-foreground text-center py-4">
                                  No hay documentos
                                </p>
                              ) : (
                                <>
                                  {/* RESUMEN: Proformas y Unidades */}
                                  <div className="grid grid-cols-2 gap-3 p-3 rounded bg-muted/20 border border-border/50">
                                    <div className="text-center">
                                      <div className="text-2xl font-bold text-foreground">
                                        {new Set(docs.map(d => d.codigo_proforma)).size}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">Proformas</div>
                                    </div>
                                    <div className="text-center">
                                      <div className="text-2xl font-bold text-foreground">
                                        {new Set(docs.map(d => d.codigo_unidad)).size}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">Unidades</div>
                                    </div>
                                  </div>

                                  {/* DOCUMENTOS POR TIPO CON ICONOS */}
                                  <div className="space-y-2 p-3 rounded bg-muted/20 border border-border/50">
                                    <div className="text-sm font-semibold text-foreground mb-2">Documentos por tipo</div>
                                    {(() => {
                                      const typeCount = docs.reduce((acc, doc) => {
                                        acc[doc.tipo_documento] = (acc[doc.tipo_documento] || 0) + 1;
                                        return acc;
                                      }, {} as Record<string, number>);
                                      
                                      // Mostrar TODOS los tipos en orden, aunque sean 0
                                      return documentTypes
                                        .map((type) => {
                                          const count = typeCount[type] || 0;
                                          return { type, count };
                                        })
                                        .sort((a, b) => b.count - a.count)
                                        .map(({ type, count }) => (
                                          <div key={type} className="flex items-center justify-between p-2 rounded bg-background/50 border border-border/30">
                                            <div className="flex items-center gap-2">
                                              <div className="text-muted-foreground">
                                                {getDocTypeIcon(type)}
                                              </div>
                                              <span className="text-sm font-medium text-foreground">{type}</span>
                                            </div>
                                            <Badge variant={count > 0 ? "secondary" : "outline"} className="font-semibold">
                                              {count}
                                            </Badge>
                                          </div>
                                        ));
                                    })()}
                                  </div>
                                </>
                              )}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {filteredProjects.length === 0 && (
                  <Card className="text-center py-12 col-span-full">
                    <CardContent>
                      <FileTextIcon className="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
                      <p className="text-muted-foreground">
                        {searchQuery ? 'No hay proyectos que coincidan con tu búsqueda' : 'No hay proyectos disponibles'}
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
