import axios, { AxiosInstance, AxiosError } from 'axios';

// ============================================================================
// API CLIENT CONFIGURATION
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// TYPES
// ============================================================================

export interface Document {
  codigo_proforma: string;
  documento_cliente: string;
  codigo_proyecto: string;
  codigo_unidad: string;
  url: string;
  nombre_archivo: string;
  fecha_carga: string;
  tipo_documento: string;
}

export interface ProjectSummary {
  codigo_proyecto: string;
  total_documentos: number;
  ultima_actualizacion: string;
}

export interface DocumentListResponse {
  total: number;
  documents: Document[];
}

export interface ProjectListResponse {
  total: number;
  projects: ProjectSummary[];
}

export interface Project {
  codigo_proyecto: string;
  nombre_proyecto: string;
  total_documentos?: number;
  ultima_fecha_carga?: string;
}

export interface ProjectsResponse {
  total: number;
  projects: Project[];
}

export interface DocumentType {
  tipo_documento: string;
}

export interface DocumentTypesResponse {
  total: number;
  types: DocumentType[];
}

export interface HealthResponse {
  status: string;
  version: string;
  redshift_connected: boolean;
}

export interface DocumentFilters {
  project_code?: string;
  document_types?: string; // CSV separado por coma
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface DownloadZipRequest {
  project_code?: string;
  document_type?: string;
  start_date?: string;
  end_date?: string;
  document_ids?: string[];
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

export async function healthCheck(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}

export async function getProjects(): Promise<ProjectListResponse> {
  const response = await apiClient.get<ProjectListResponse>('/projects');
  return response.data;
}

export async function getProjectOptions(): Promise<string[]> {
  const response = await apiClient.get<{ options: string[] }>('/filters/projects');
  return response.data.options;
}

export async function getProjectsList(): Promise<ProjectsResponse> {
  const response = await apiClient.get<ProjectsResponse>('/projects/all');
  return response.data;
}

export async function getProjectOptionsSearch(query: string, limit: number = 50): Promise<string[]> {
  const response = await apiClient.get<{ options: string[] }>('/filters/projects', {
    params: { q: query, limit },
  });
  return response.data.options;
}

export async function getDocumentTypeOptions(): Promise<string[]> {
  const response = await apiClient.get<{ options: string[] }>('/filters/document-types');
  return response.data.options;
}

export async function getDocumentTypesList(): Promise<DocumentTypesResponse> {
  const response = await apiClient.get<DocumentTypesResponse>('/document-types/all');
  return response.data;
}

export async function getDocuments(filters?: DocumentFilters): Promise<DocumentListResponse> {
  const response = await apiClient.get<DocumentListResponse>('/documents', {
    params: filters,
  });
  return response.data;
}

export async function downloadDocument(codigoProforma: string): Promise<void> {
  const response = await apiClient.get(`/download/document/${codigoProforma}`, {
    responseType: 'blob',
  });
  
  const contentDisposition = response.headers['content-disposition'];
  let filename = `${codigoProforma}.pdf`;
  
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }
  
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export async function downloadZip(request: DownloadZipRequest): Promise<void> {
  const response = await apiClient.post('/download/zip', request, {
    responseType: 'blob',
    timeout: 300000, // 5 minutos para archivos grandes
  });
  
  const contentDisposition = response.headers['content-disposition'];
  let filename = 'tale_documents.zip';
  
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }
  
  const blob = new Blob([response.data], { type: 'application/zip' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export async function downloadProjectZip(projectCode: string, queryString?: string): Promise<void> {
  const url = `/download/zip/project/${projectCode}${queryString ? queryString : ''}`;
  const response = await apiClient.get(url, {
    responseType: 'blob',
    timeout: 300000, // 5 minutos para archivos grandes
  });
  
  const blob = new Blob([response.data], { type: 'application/zip' });
  const urlObj = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = urlObj;
  link.download = `${projectCode}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(urlObj);
}

export function handleApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; error?: string }>;
    
    if (axiosError.response) {
      const detail = axiosError.response.data?.detail || axiosError.response.data?.error;
      return detail || `Error ${axiosError.response.status}: ${axiosError.response.statusText}`;
    } else if (axiosError.request) {
      return 'Error de conexión. Verifique que el backend esté ejecutándose.';
    }
  }
  
  return 'Error desconocido. Intente nuevamente.';
}
