"""
Servicio de conexión y consulta a AWS Redshift (Read-Only)
"""
import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any, Optional
from backend.core.config import settings

class RedshiftService:
    """Servicio para consultas read-only a Redshift"""
    
    def __init__(self):
        """Inicializa el connection pool"""
        self.connection_pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Crea el connection pool a Redshift"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=settings.REDSHIFT_HOST,
                port=settings.REDSHIFT_PORT,
                database=settings.REDSHIFT_DATABASE,
                user=settings.REDSHIFT_USER,
                password=settings.REDSHIFT_PASSWORD,
                connect_timeout=10
            )
            print("✅ Redshift connection pool initialized")
        except Exception as e:
            print(f"❌ Error initializing Redshift pool: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Ejecuta una query SELECT y retorna resultados como lista de diccionarios"""
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed (read-only)")
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"❌ Error executing query: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def get_projects_summary(self) -> List[Dict[str, Any]]:
        """Obtiene resumen de proyectos con total de documentos"""
        query = """
        SELECT 
            codigo_proyecto,
            COUNT(*) as total_documentos,
            MAX(fecha_carga) as ultima_actualizacion
        FROM tale.archivos
        WHERE codigo_proyecto IS NOT NULL
        GROUP BY codigo_proyecto
        ORDER BY codigo_proyecto
        """
        return self.execute_query(query)
    
    def get_documents(
        self,
        project_code: Optional[str] = None,
        document_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene lista de documentos con filtros opcionales"""
        conditions = []
        params = []
        
        if project_code:
            conditions.append("codigo_proyecto = %s")
            params.append(project_code)
        
        if document_type:
            conditions.append("tipo_documento = %s")
            params.append(document_type)
        
        if start_date:
            conditions.append("fecha_carga >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("fecha_carga <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT 
            codigo_proforma,
            documento_cliente,
            codigo_proyecto,
            codigo_unidad,
            url,
            nombre_archivo,
            fecha_carga,
            tipo_documento
        FROM tale.archivos
        WHERE {where_clause}
        ORDER BY fecha_carga DESC
        LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        return self.execute_query(query, tuple(params))
    
    def get_document_by_codigo(self, codigo_proforma: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento específico por código de proforma"""
        query = """
        SELECT 
            codigo_proforma,
            documento_cliente,
            codigo_proyecto,
            codigo_unidad,
            url,
            nombre_archivo,
            fecha_carga,
            tipo_documento
        FROM tale.archivos
        WHERE codigo_proforma = %s
        LIMIT 1
        """
        results = self.execute_query(query, (codigo_proforma,))
        return results[0] if results else None
    
    def get_project_codes(self) -> List[str]:
        """Obtiene lista única de códigos de proyecto"""
        query = """
        SELECT DISTINCT codigo_proyecto
        FROM tale.archivos
        WHERE codigo_proyecto IS NOT NULL
        ORDER BY codigo_proyecto
        """
        results = self.execute_query(query)
        return [row['codigo_proyecto'] for row in results]
    
    def get_document_types(self) -> List[str]:
        """Obtiene lista única de tipos de documento"""
        query = """
        SELECT DISTINCT tipo_documento
        FROM tale.archivos
        WHERE tipo_documento IS NOT NULL
        ORDER BY tipo_documento
        """
        results = self.execute_query(query)
        return [row['tipo_documento'] for row in results]
    
    def test_connection(self) -> bool:
        """Prueba la conexión a Redshift"""
        try:
            self.execute_query("SELECT 1 as test")
            return True
        except:
            return False
    
    def close(self):
        """Cierra el connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            print("✅ Redshift connection pool closed")

redshift_service = RedshiftService()
