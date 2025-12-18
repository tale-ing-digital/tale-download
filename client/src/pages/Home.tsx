import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Layout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { SearchIcon, DownloadIcon, PackageIcon, FileTextIcon, CalendarIcon } from '@/lib/icons';
import {
  getProjects,
  getDocuments,
  downloadDocument,
  downloadProjectZip,
  handleApiError,
  type Document,
  type ProjectSummary,
  type DocumentFilters,
} from '@/lib/api';

export default function Home() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  
  const [filters, setFilters] = useState<DocumentFilters>({
    project_code: '',
    document_type: '',
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    loadProjects();
    loadDocuments();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await getProjects();
      setProjects(response.projects);
    } catch (error) {
      toast.error(handleApiError(error));
    }
  };

  const loadDocuments = async (customFilters?: DocumentFilters) => {
    setLoading(true);
    try {
      const activeFilters = customFilters || filters;
      const cleanFilters: DocumentFilters = {};
      
      if (activeFilters.project_code) cleanFilters.project_code = activeFilters.project_code;
      if (activeFilters.document_type) cleanFilters.document_type = activeFilters.document_type;
      if (activeFilters.start_date) cleanFilters.start_date = activeFilters.start_date;
      if (activeFilters.end_date) cleanFilters.end_date = activeFilters.end_date;
      
      const response = await getDocuments(Object.keys(cleanFilters).length > 0 ? cleanFilters : undefined);
      setDocuments(response.documents);
      
      if (response.total === 0) {
        toast.info('No se encontraron documentos con los filtros aplicados');
      }
    } catch (error) {
      toast.error(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadDocuments();
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

  const handleProjectClick = (projectCode: string) => {
    const newFilters = { ...filters, project_code: projectCode };
    setFilters(newFilters);
    loadDocuments(newFilters);
  };

  const handleClearFilters = () => {
    const emptyFilters: DocumentFilters = {
      project_code: '',
      document_type: '',
      start_date: '',
      end_date: '',
    };
    setFilters(emptyFilters);
    loadDocuments(emptyFilters);
  };

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
                  <Input
                    placeholder="Código de proyecto"
                    value={filters.project_code || ''}
                    onChange={(e) => setFilters({ ...filters, project_code: e.target.value })}
                  />
                  <Input
                    placeholder="Tipo de documento"
                    value={filters.document_type || ''}
                    onChange={(e) => setFilters({ ...filters, document_type: e.target.value })}
                  />
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
                  <Button onClick={handleSearch} variant="talePrimary" className="flex-1">
                    <SearchIcon className="mr-2" />
                    Buscar
                  </Button>
                  <Button onClick={handleClearFilters} variant="taleSecondary">
                    Limpiar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {projects.length > 0 && (
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

            <div>
              <h2 className="text-2xl font-semibold text-foreground mb-6">
                Documentos
                {documents.length > 0 && (
                  <span className="text-muted-foreground text-lg ml-2">
                    ({documents.length})
                  </span>
                )}
              </h2>

              {loading ? (
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
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {documents.map((doc) => (
                    <Card
                      key={doc.codigo_proforma}
                      className="group hover:border-primary/50 transition-all duration-200"
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
                          onClick={() => handleDownloadDocument(doc.codigo_proforma)}
                          disabled={downloading === doc.codigo_proforma}
                        >
                          <DownloadIcon className="mr-2" />
                          {downloading === doc.codigo_proforma ? 'Descargando...' : 'Descargar PDF'}
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
