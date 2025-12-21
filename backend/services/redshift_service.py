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
            print(f"🔌 Intentando conectar a Redshift...")
            print(f"   Host: {settings.REDSHIFT_HOST}")
            print(f"   Port: {settings.REDSHIFT_PORT}")
            print(f"   Database: {settings.REDSHIFT_DATABASE}")
            print(f"   User: {settings.REDSHIFT_USER}")
            
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
            print(f"   Tipo de error: {type(e).__name__}")
            print("⚠️  Backend will start but Redshift features will not work")
            self.connection_pool = None
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Ejecuta una query SELECT y retorna resultados como lista de diccionarios"""
        if not self.connection_pool:
            raise RuntimeError("Redshift connection not available. Please configure REDSHIFT_* environment variables.")
        
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
            
            # Check if cursor has a description (SELECT worked)
            if cursor.description is None:
                return []
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"❌ Error executing query: {e}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def get_projects_summary(self) -> List[Dict[str, Any]]:
        """Obtiene resumen de proyectos con total de documentos"""
        query = """
        SELECT 
            pu.codigo_proyecto,
            COUNT(*) as total_documentos,
            TO_CHAR(MAX(a.fecha_carga), 'YYYY-MM-DD HH24:MI:SS') as ultima_actualizacion
        FROM tale.archivos a
        LEFT JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
        WHERE pu.codigo_proyecto IS NOT NULL
        GROUP BY pu.codigo_proyecto
        ORDER BY pu.codigo_proyecto
        """
        return self.execute_query(query)
    
    def get_documents(
        self,
        project_code: Optional[str] = None,
        document_types: Optional[list] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtiene documentos con filtros por proyecto real (codigo_proyecto)
        Relación: archivos → proforma_unidad → proyectos
        
        Args:
            project_code: Código del proyecto
            document_types: Lista de tipos de documento para filtrado
            start_date: Fecha inicio
            end_date: Fecha fin
            limit: Límite de resultados
            offset: Offset para paginación
        """
        conditions = []
        params_list = []
        
        # FILTRO PRINCIPAL: proforma_unidad.codigo_proyecto (NO entidad_id)
        if project_code:
            conditions.append("pu.codigo_proyecto = %s")
            params_list.append(project_code)
        
        if start_date:
            conditions.append("a.fecha_carga >= %s")
            params_list.append(start_date)
        
        if end_date:
            conditions.append("a.fecha_carga <= %s")
            params_list.append(end_date)
        
        # MULTI-SELECCIÓN de tipos (frontend envía lista)
        # Si viene lista de tipos, hacemos OR de los tipos
        if document_types and len(document_types) > 0:
            type_conditions = []
            for doc_type in document_types:
                type_conditions.append(
                    f"""CASE 
                        WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%voucher%%' OR
                             LOWER(COALESCE(a.nombre, '')) LIKE '%%constancia%%' OR
                             LOWER(COALESCE(a.nombre, '')) LIKE '%%transf%%' OR
                             LOWER(COALESCE(a.nombre, '')) LIKE '%%vou%%' OR
                             LOWER(COALESCE(a.nombre, '')) LIKE '%%pago%%' OR
                             LOWER(COALESCE(a.nombre, '')) LIKE '%%sep%%' THEN 'Voucher'
                        WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%minuta%%' THEN 'Minuta'
                        WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%adenda%%' THEN 'Adenda'
                        WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%carta%%' OR LOWER(COALESCE(a.nombre, '')) LIKE '%%aprobac%%' THEN 'Carta de Aprobación'
                        ELSE 'Otro'
                    END = %s"""
                )
                params_list.append(doc_type)
            
            if type_conditions:
                conditions.append(f"({' OR '.join(type_conditions)})")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # IMPORTANT: LIMIT and OFFSET must be literal integers, NOT parametrized
        query = f"""
        SELECT 
            a.codigo_proforma,
            pu.documento_cliente,
            c.nombres || ' ' || c.apellidos AS nombre_cliente,
            pu.codigo_proyecto,
            pu.codigo_unidad,
            CASE
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%departamento%%' THEN 'DPTO'
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%estacionamiento%%' THEN 'EST'
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%depósito%%' OR 
                     LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%deposito%%' THEN 'DEP'
                ELSE 'OTRO'
            END AS tipo_unidad,
            a.url,
            a.nombre as nombre_archivo,
            a.montaje,
            TO_CHAR(a.fecha_carga, 'YYYY-MM-DD HH24:MI:SS') as fecha_carga,
            CASE
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%voucher%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%constancia%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%transf%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%vou%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%pago%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%sep%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%voucher%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%pago%%' THEN 'Voucher'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%minuta%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%minuta%%' THEN 'Minuta'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%adenda%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%adenda%%' THEN 'Adenda'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%carta%%' OR 
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%aprobac%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%carta%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%aprobac%%' THEN 'Carta de Aprobación'
                ELSE 'Otro'
            END as tipo_documento
        FROM tale.archivos a
        INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
        LEFT JOIN tale.clientes c ON pu.documento_cliente = c.documento
        WHERE a.entidad <> 'Unidad' AND {where_clause}
        ORDER BY a.fecha_carga DESC
        LIMIT {limit} OFFSET {offset}
        """
        
        # Convert to tuple
        params = tuple(params_list) if params_list else None
        
        result = self.execute_query(query, params)
        return result
    
    def get_document_by_codigo(self, codigo_proforma: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento específico por código de proforma"""
        query = """
        SELECT 
            a.codigo_proforma,
            pu.documento_cliente,
            c.nombres || ' ' || c.apellidos AS nombre_cliente,
            pu.codigo_proyecto,
            pu.codigo_unidad,
            CASE
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%departamento%%' THEN 'DPTO'
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%estacionamiento%%' THEN 'EST'
                WHEN LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%depósito%%' OR 
                     LOWER(COALESCE(pu.tipo_unidad, '')) LIKE '%%deposito%%' THEN 'DEP'
                ELSE 'OTRO'
            END AS tipo_unidad,
            a.url,
            a.nombre as nombre_archivo,
            a.montaje,
            TO_CHAR(a.fecha_carga, 'YYYY-MM-DD HH24:MI:SS') as fecha_carga,
            CASE 
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%voucher%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%constancia%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%transf%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%vou%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%pago%%' OR
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%sep%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%voucher%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%pago%%' THEN 'Voucher'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%minuta%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%minuta%%' THEN 'Minuta'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%adenda%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%adenda%%' THEN 'Adenda'
                WHEN LOWER(COALESCE(a.nombre, '')) LIKE '%%carta%%' OR 
                     LOWER(COALESCE(a.nombre, '')) LIKE '%%aprobac%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%carta%%' OR
                     LOWER(COALESCE(a.montaje, '')) LIKE '%%aprobac%%' THEN 'Carta de Aprobación'
                ELSE 'Otro'
            END as tipo_documento
        FROM tale.archivos a
        INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
        LEFT JOIN tale.clientes c ON pu.documento_cliente = c.documento
        WHERE a.codigo_proforma = %s
        LIMIT 1
        """
        results = self.execute_query(query, (codigo_proforma,))
        return results[0] if results else None
    
    def get_project_codes(self, search_query: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """Obtiene lista única de códigos de proyecto con búsqueda opcional desde proforma_unidad"""
        params = []
        where_clauses = ["pu.codigo_proyecto IS NOT NULL"]
        
        if search_query:
            # Buscar por código O por nombre del proyecto
            where_clauses.append(
                "("
                "LOWER(pu.codigo_proyecto) LIKE %s OR "
                "LOWER(pu.nombre_proyecto) LIKE %s"
                ")"
            )
            search_param = f"%{search_query.lower()}%"
            params.extend([search_param, search_param])
        
        where_clause = " AND ".join(where_clauses)
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT DISTINCT pu.codigo_proyecto
        FROM tale.proforma_unidad pu
        WHERE {where_clause}
        ORDER BY pu.codigo_proyecto
        {limit_clause}
        """
        
        results = self.execute_query(query, params if params else None)
        return [r['codigo_proyecto'] for r in results] if results else []
        results = self.execute_query(query, tuple(params) if params else None)
        return [str(row['codigo_proyecto']) for row in results]

    def get_projects_with_names(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Obtiene proyectos con sus nombres desde DIM o tabla de referencia"""
        query = """
        SELECT 
            pu.codigo_proyecto,
            pu.nombre_proyecto,
            COUNT(*) as total_documentos,
            MAX(a.fecha_carga) as ultima_fecha_carga
        FROM tale.proforma_unidad pu
        INNER JOIN tale.archivos a ON a.codigo_proforma = pu.codigo_proforma
        WHERE pu.codigo_proyecto IS NOT NULL 
          AND pu.nombre_proyecto IS NOT NULL
        GROUP BY pu.codigo_proyecto, pu.nombre_proyecto
        ORDER BY pu.codigo_proyecto
        """
        if limit:
            query += f" LIMIT {limit}"
        
        results = self.execute_query(query)
        return results

    def get_document_types_homologated(self) -> List[Dict[str, Any]]:
        """Obtiene tipos de documento homologados/categorizados (desde el CASE del SQL)"""
        # Estos son los tipos homologados que devuelven el CASE statement en get_documents
        return [
            {"tipo_documento": "Voucher"},
            {"tipo_documento": "Minuta"},
            {"tipo_documento": "Adenda"},
            {"tipo_documento": "Carta de Aprobación"},
            {"tipo_documento": "Otro"}
        ]
    
    def get_document_codes(self, search_query: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """Obtiene lista única de tipos de documento"""
        query = """
        SELECT DISTINCT montaje as tipo_documento
        FROM tale.archivos
        WHERE montaje IS NOT NULL
        ORDER BY montaje
        """
        results = self.execute_query(query)
        return [row['tipo_documento'] for row in results]
    
    def get_table_columns(self) -> List[str]:
        """Obtiene las columnas de la tabla archivos"""
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'tale' AND table_name = 'archivos'
        ORDER BY ordinal_position
        """
        try:
            results = self.execute_query(query)
            return [row['column_name'] for row in results]
        except Exception as e:
            print(f"❌ Error getting columns: {e}")
            # Fallback: intentar obtener una fila y extraer las columnas
            try:
                sample = self.execute_query("SELECT * FROM tale.archivos LIMIT 1")
                if sample:
                    return list(sample[0].keys())
            except:
                pass
            return []
    
    def diagnose_tables(self) -> dict:
        """Diagnóstico: busca tablas relevantes en el schema tale"""
        diagnosis = {
            "archivos_columns": [],
            "proyectos_exists": False,
            "proyectos_columns": [],
            "proforma_unidad_exists": False,
            "sample_archivos": [],
            "relationship_test": []
        }
        
        try:
            # Verificar columnas de archivos
            columns_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'tale' AND table_name = 'archivos'
            ORDER BY ordinal_position
            """
            diagnosis["archivos_columns"] = [row['column_name'] for row in self.execute_query(columns_query)]
            
            # Verificar si existe tale.proyectos
            proyectos_check = """
            SELECT COUNT(*) as count FROM information_schema.tables 
            WHERE table_schema = 'tale' AND table_name = 'proyectos'
            """
            result = self.execute_query(proyectos_check)
            diagnosis["proyectos_exists"] = result[0]['count'] > 0 if result else False
            
            if diagnosis["proyectos_exists"]:
                proyectos_cols = """
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'tale' AND table_name = 'proyectos'
                ORDER BY ordinal_position
                """
                diagnosis["proyectos_columns"] = [row['column_name'] for row in self.execute_query(proyectos_cols)]
            
            # Verificar si existe proforma_unidad
            proforma_check = """
            SELECT COUNT(*) as count FROM information_schema.tables 
            WHERE table_schema = 'tale' AND table_name = 'proforma_unidad'
            """
            result = self.execute_query(proforma_check)
            diagnosis["proforma_unidad_exists"] = result[0]['count'] > 0 if result else False
            
            # Sample de archivos
            sample = """
            SELECT DISTINCT entidad_id, entidad 
            FROM tale.archivos 
            WHERE entidad_id IS NOT NULL
            LIMIT 10
            """
            diagnosis["sample_archivos"] = self.execute_query(sample)
            
            # Test relationship: archivos → proforma_unidad → proyectos
            if diagnosis["proforma_unidad_exists"]:
                proforma_cols = """
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'tale' AND table_name = 'proforma_unidad'
                ORDER BY ordinal_position
                """
                diagnosis["proforma_unidad_columns"] = [row['column_name'] for row in self.execute_query(proforma_cols)]
                
                relationship_test = """
                SELECT 
                    a.entidad_id,
                    pu.*
                FROM tale.archivos a
                LEFT JOIN tale.proforma_unidad pu ON a.entidad_id = pu.id
                LIMIT 1
                """
                try:
                    diagnosis["relationship_test"] = self.execute_query(relationship_test)
                except:
                    diagnosis["relationship_test"] = "Query failed - checking columns..."
            
        except Exception as e:
            diagnosis["error"] = str(e)
        
        return diagnosis
    
    def test_connection(self) -> bool:
        """Prueba la conexión a Redshift"""
        if not self.connection_pool:
            return False
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
