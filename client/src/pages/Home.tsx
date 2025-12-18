import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Layout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SearchIcon, DownloadIcon, PackageIcon, FileTextIcon, CalendarIcon } from '@/lib/icons';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  getProjects,
  getDocuments,
  getProjectOptions,
  getDocumentTypeOptions,
  downloadDocument,
  downloadProjectZip,
  downloadZip,
  handleApiError,
  type Document,
  type ProjectSummary,
  type DocumentFilters,
} from '@/lib/api';

export default function Home() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [projectOptions, setProjectOptions] = useState<string[]>([]);
  const [documentTypeOptions, setDocumentTypeOptions] = useState<string[]>([]);
  
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  
  const [filters, setFilters] = useState<DocumentFilters>({
    project_code: '',
    document_type: '',
    start_date: '',
    end_date: '',
  });

  const [pagination, setPagination] = useState({
    page: 1,
    limit: 25,
    total: 0,
  });

  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [projectsData, projectOpts, docTypeOpts] = await Promise.all([
        getProjects(),
        getProjectOptions(),
        getDocumentTypeOptions(),
      ]);
      
      setProjects(projectsData.projects);
      setProjectOptions(projectOpts);
      setDocumentTypeOptions(docTypeOpts);
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async (page: number = 1) => {
    setSearching(true);
    try {
      const cleanFilters: DocumentFilters = {};
      
      if (filters.project_code) cleanFilters.project_code = filters.project_code;
      if (filters.document_type) cleanFilters.document_type = filters.document_type;
      if (filters.start_date) cleanFilters.start_date = filters.start_date;
      if (filters.end_date) cleanFilters.end_date = filters.end_date;
      
      const offset = (page - 1) * pagination.limit;
      const response = await getDocuments({
        ...cleanFilters,
        limit: pagination.limit,
        offset,
      });
      
      setDocuments(response.documents);
      setPagination(prev => ({ ...prev, page, total: response.total }));
      setHasSearched(true);
      setSelectedDocuments(new Set());
      
      if (response.total === 0) {
        toast.info('No se encontraron documentos con los filtros aplicados');
      }
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setSearching(false);
    }
  };

  const handleSearch = () => {
    if (!filters.project_code && !filters.document_type && !filters.start_date && !filters.end_date) {
      toast.error('Debe aplicar al menos un filtro para buscar');
      return;
    }
    loadDocuments(1);
  };

  const handleDownloadDocument = async (codigo: string) => {
    setDownloading(codigo);
    try {
      await downloadDocument(codigo);
      toast.success('Documento descargado exitosamente');
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadProjectZip = async (projectCode: string) => {
    setDownloading(projectCode);
    try {
      await downloadProjectZip(projectCode);
      toast.success(`ZIP del proyecto ${projectCode} descargado exitosamente`);
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadSelected = async () => {
    if (selectedDocuments.size === 0) {
      toast.error('Debe seleccionar al menos un documento');
      return;
    }

    setDownloading('selected');
    try {
      await downloadZip({ document_ids: Array.from(selectedDocuments) });
      toast.success(`${selectedDocuments.size} documentos descargados exitosamente`);
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setDownloading(null);
    }
  };

  const handleSelectAll = () => {
    if (selectedDocuments.size === documents.length) {
      setSelectedDocuments(new Set());
    } else {
      setSelectedDocuments(new Set(documents.map(d => d.codigo_proforma)));
    }
  };

  const handleProjectClick = (projectCode: string) => {
    setFilters({ ...filters, project_code: projectCode });
    setTimeout(() => {
      const cleanFilters = { ...filters, project_code: projectCode };
      loadDocuments(1);
    }, 100);
  };

  const handleClearFilters = () => {
    setFilters({
      project_code: '',
      document_type: '',
      start_date: '',
      end_date: '',
    });
    setDocuments([]);
    setHasSearched(false);
    setSelectedDocuments(new Set());
  };

  const totalPages = Math.ceil(pagination.total / pagination.limit);

  return (
    <Layout>
      <div className="min-h-screen bg-background">
        <section className="py-16 px-4">
          <div className="container max-w-7xl">
            <div className="text-center mb-12">
              <h1 className="text-4xl font-bold text-foreground mb-4">
                Exportación Documental
              </h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Consulta y descarga documentos desde Business Intelligence
              </p>
            </div>

            <Card className="mb-8 backdrop-blur-sm bg-card/95 border-border/50">
              <CardContent className="pt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <Select
                    value={filters.project_code || ''}
                    onValueChange={(value) => setFilters({ ...filters, project_code: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Código de proyecto" />
                    </SelectTrigger>
                    <SelectContent>
                      {projectOptions.map((code) => (
                        <SelectItem key={code} value={code}>
                          {code}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={filters.document_type || ''}
                    onValueChange={(value) => setFilters({ ...filters, document_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Tipo de documento" />
                    </SelectTrigger>
                    <SelectContent>
                      {documentTypeOptions.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Input
                    type="date"
                    placeholder="Fecha inicio"
                    value={filters.start_date || ''}
                    onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                  />
                  <Input
                    type="date"
                    placeholder="Fecha fin"
                    value={filters.end_date || ''}
                    onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                  />
                </div>
                <div className="flex gap-3">
                  <Button onClick={handleSearch} variant="talePrimary" className="flex-1" disabled={searching}>
                    <SearchIcon className="mr-2" />
                    {searching ? 'Buscando...' : 'Buscar'}
                  </Button>
                  <Button onClick={handleClearFilters} variant="taleSecondary">
                    Limpiar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                {[1, 2, 3].map((i) => (
                  <Card key={i}>
                    <CardHeader>
                      <Skeleton className="h-6 w-3/4" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-4 w-full mb-2" />
                      <Skeleton className="h-10 w-full" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : projects.length > 0 && (
              <div className="mb-12">
                <h2 className="text-2xl font-semibold text-foreground mb-6">Proyectos</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {projects.map((project) => (
                    <Card
                      key={project.codigo_proyecto}
                      className="group hover:border-primary/50 transition-all duration-200 cursor-pointer"
                      onClick={() => handleProjectClick(project.codigo_proyecto)}
                    >
                      <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                          <span className="flex items-center gap-2">
                            <PackageIcon />
                            {project.codigo_proyecto}
                          </span>
                          <Badge variant="tale">{project.total_documentos}</Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                          <CalendarIcon className="w-4 h-4" />
                          <span>{project.ultima_actualizacion}</span>
                        </div>
                        <Button
                          variant="taleSecondary"
                          size="sm"
                          className="w-full"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadProjectZip(project.codigo_proyecto);
                          }}
                          disabled={downloading === project.codigo_proyecto}
                        >
                          <DownloadIcon className="mr-2" />
                          {downloading === project.codigo_proyecto ? 'Descargando...' : 'Descargar ZIP'}
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {hasSearched && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-semibold text-foreground">
                    Documentos
                    {documents.length > 0 && (
                      <span className="text-muted-foreground text-lg ml-2">
                        ({pagination.total} total)
                      </span>
                    )}
                  </h2>
                  
                  {documents.length > 0 && (
                    <div className="flex gap-3">
                      <Button variant="taleSecondary" size="sm" onClick={handleSelectAll}>
                        {selectedDocuments.size === documents.length ? 'Deseleccionar todos' : 'Seleccionar todos'}
                      </Button>
                      {selectedDocuments.size > 0 && (
                        <Button
                          variant="talePrimary"
                          size="sm"
                          onClick={handleDownloadSelected}
                          disabled={downloading === 'selected'}
                        >
                          <DownloadIcon className="mr-2" />
                          Descargar seleccionados ({selectedDocuments.size})
                        </Button>
                      )}
                    </div>
                  )}
                </div>

                {searching ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <Card key={i}>
                        <CardHeader>
                          <Skeleton className="h-6 w-3/4" />
                        </CardHeader>
                        <CardContent>
                          <Skeleton className="h-4 w-full mb-2" />
                          <Skeleton className="h-4 w-2/3 mb-4" />
                          <Skeleton className="h-10 w-full" />
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : documents.length === 0 ? (
                  <Card className="text-center py-12">
                    <CardContent>
                      <FileTextIcon className="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
                      <p className="text-muted-foreground">
                        No se encontraron documentos. Ajusta los filtros de búsqueda.
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
                      {documents.map((doc) => {
                        const isSelected = selectedDocuments.has(doc.codigo_proforma);
                        return (
                          <Card
                            key={doc.codigo_proforma}
                            className={`group hover:border-primary/50 transition-all duration-200 cursor-pointer ${
                              isSelected ? 'border-primary ring-2 ring-primary/20' : ''
                            }`}
                            onClick={() => {
                              const newSelected = new Set(selectedDocuments);
                              if (isSelected) {
                                newSelected.delete(doc.codigo_proforma);
                              } else {
                                newSelected.add(doc.codigo_proforma);
                              }
                              setSelectedDocuments(newSelected);
                            }}
                          >
                            <CardHeader>
                              <CardTitle className="text-base flex items-center justify-between">
                                <span className="truncate">{doc.documento_cliente}</span>
                                <Badge variant="tale">{doc.tipo_documento}</Badge>
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="space-y-2 text-sm text-muted-foreground mb-4">
                                <div className="flex justify-between">
                                  <span className="font-medium">Proforma:</span>
                                  <span>{doc.codigo_proforma}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="font-medium">Proyecto:</span>
                                  <span>{doc.codigo_proyecto}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="font-medium">Unidad:</span>
                                  <span>{doc.codigo_unidad}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="font-medium">Fecha:</span>
                                  <span>{doc.fecha_carga}</span>
                                </div>
                              </div>
                              <Button
                                variant="talePrimary"
                                size="sm"
                                className="w-full"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDownloadDocument(doc.codigo_proforma);
                                }}
                                disabled={downloading === doc.codigo_proforma}
                              >
                                <DownloadIcon className="mr-2" />
                                {downloading === doc.codigo_proforma ? 'Descargando...' : 'Descargar PDF'}
                              </Button>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>

                    {totalPages > 1 && (
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="taleSecondary"
                          size="sm"
                          onClick={() => loadDocuments(pagination.page - 1)}
                          disabled={pagination.page === 1 || searching}
                        >
                          <ChevronLeft className="w-4 h-4" />
                          Anterior
                        </Button>
                        <span className="text-sm text-muted-foreground px-4">
                          Página {pagination.page} de {totalPages}
                        </span>
                        <Button
                          variant="taleSecondary"
                          size="sm"
                          onClick={() => loadDocuments(pagination.page + 1)}
                          disabled={pagination.page === totalPages || searching}
                        >
                          Siguiente
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </Layout>
  );
}
