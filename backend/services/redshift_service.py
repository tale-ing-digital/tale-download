"""
Servicio de conexión y consulta a AWS Redshift (Read-Only)
"""
import hashlib
import logging
import time
import threading
import psycopg2
import psycopg2.pool
from typing import List, Dict, Any, Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class RedshiftService:
    """Servicio para consultas read-only a Redshift con reconexión automática"""
    
    def __init__(self):
        """Inicializa el connection pool"""
        self.connection_pool = None
        self._pool_lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Crea el connection pool a Redshift con TCP keepalive"""
        try:
            print(f"🔌 Intentando conectar a Redshift...")
            print(f"   Host: {settings.REDSHIFT_HOST}")
            print(f"   Port: {settings.REDSHIFT_PORT}")
            print(f"   Database: {settings.REDSHIFT_DATABASE}")
            print(f"   User: {settings.REDSHIFT_USER}")
            
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=settings.REDSHIFT_POOL_MIN,
                maxconn=settings.REDSHIFT_POOL_MAX,
                host=settings.REDSHIFT_HOST,
                port=settings.REDSHIFT_PORT,
                database=settings.REDSHIFT_DATABASE,
                user=settings.REDSHIFT_USER,
                password=settings.REDSHIFT_PASSWORD,
                connect_timeout=10,
                # TCP keepalive: prevents AWS/NAT from silently killing idle connections
                keepalives=1,
                keepalives_idle=settings.REDSHIFT_KEEPALIVE_IDLE,
                keepalives_interval=10,
                keepalives_count=3,
                options=f'-c statement_timeout={settings.REDSHIFT_QUERY_TIMEOUT}',
            )
            print("✅ Redshift ThreadedConnectionPool initialized "
                  f"(min={settings.REDSHIFT_POOL_MIN}, max={settings.REDSHIFT_POOL_MAX}, "
                  f"keepalive_idle={settings.REDSHIFT_KEEPALIVE_IDLE}s, "
                  f"query_timeout={settings.REDSHIFT_QUERY_TIMEOUT}ms)")
        except Exception as e:
            print(f"❌ Error initializing Redshift pool: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            print("⚠️  Backend will start but Redshift features will not work")
            self.connection_pool = None

    def _ensure_pool(self):
        """Ensures the connection pool is available, re-initializing if needed."""
        if self.connection_pool is not None:
            return
        with self._pool_lock:
            # Double-check after acquiring lock
            if self.connection_pool is None:
                print("🔄 Connection pool is None, attempting re-initialization...")
                self._initialize_pool()
        if self.connection_pool is None:
            raise RuntimeError(
                "Redshift connection not available. "
                "Please configure REDSHIFT_* environment variables."
            )

    def _reinitialize_pool(self):
        """Closes and recreates the entire connection pool."""
        with self._pool_lock:
            print("♻️  Reinitializing entire connection pool...")
            old_pool = self.connection_pool
            self.connection_pool = None
            if old_pool is not None:
                try:
                    old_pool.closeall()
                except Exception:
                    pass
            self._initialize_pool()

    def _get_valid_connection(self):
        """Gets a connection from the pool and validates it with a lightweight check."""
        t_pool_start = time.perf_counter()
        conn = self.connection_pool.getconn()
        pool_wait_ms = (time.perf_counter() - t_pool_start) * 1000
        if pool_wait_ms >= settings.REDSHIFT_SLOW_POOL_WAIT_MS:
            logger.warning(
                "[REDSHIFT] Slow pool wait: %.2fms (threshold=%sms)",
                pool_wait_ms,
                settings.REDSHIFT_SLOW_POOL_WAIT_MS,
            )

        try:
            # Fast check: psycopg2 tracks connection state
            if conn.closed:
                raise psycopg2.OperationalError("Connection is closed")
            # Lightweight validation query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
        except Exception:
            # Connection is dead — discard it and get a fresh one
            print("⚠️  Stale connection detected, discarding...")
            try:
                self.connection_pool.putconn(conn, close=True)
            except Exception:
                pass
            raise
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Ejecuta una query SELECT con retry automático y validación de conexión."""
        self._ensure_pool()
        
        # Permitir SELECT y WITH (CTEs - Common Table Expressions)
        query_upper = query.strip().upper()
        if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
            raise ValueError("Only SELECT queries are allowed (read-only)")
        
        last_error = None
        max_attempts = settings.REDSHIFT_RETRY_ATTEMPTS
        query_fingerprint = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
        params_count = len(params) if params else 0

        for attempt in range(1, max_attempts + 1):
            conn = None
            t_query_start = time.perf_counter()
            try:
                conn = self._get_valid_connection()
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if cursor.description is None:
                    cursor.close()
                    self.connection_pool.putconn(conn)
                    return []
                
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                elapsed_ms = (time.perf_counter() - t_query_start) * 1000
                if elapsed_ms >= settings.REDSHIFT_SLOW_QUERY_MS:
                    logger.warning(
                        "[REDSHIFT] Slow query fp=%s attempt=%s rows=%s elapsed=%.2fms params=%s",
                        query_fingerprint,
                        attempt,
                        len(results),
                        elapsed_ms,
                        params_count,
                    )
                else:
                    logger.info(
                        "[REDSHIFT] Query ok fp=%s attempt=%s rows=%s elapsed=%.2fms params=%s",
                        query_fingerprint,
                        attempt,
                        len(results),
                        elapsed_ms,
                        params_count,
                    )
                
                cursor.close()
                self.connection_pool.putconn(conn)
                return results
                
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                elapsed_ms = (time.perf_counter() - t_query_start) * 1000
                logger.error(
                    "[REDSHIFT] Connection/query error fp=%s attempt=%s/%s elapsed=%.2fms error=%s",
                    query_fingerprint,
                    attempt,
                    max_attempts,
                    elapsed_ms,
                    str(e),
                )
                print(f"⚠️  Connection error on attempt {attempt}/{max_attempts}: {e}")
                # Close broken connection, don't return it to pool
                if conn is not None:
                    try:
                        self.connection_pool.putconn(conn, close=True)
                    except Exception:
                        pass
                    conn = None
                # On failure, reinitialize the entire pool before retrying
                if attempt < max_attempts:
                    self._reinitialize_pool()
                    if self.connection_pool is None:
                        break
                    backoff = min(1.0 * attempt, 3.0)
                    print(f"⏳ Retrying in {backoff}s...")
                    time.sleep(backoff)
            except Exception as e:
                elapsed_ms = (time.perf_counter() - t_query_start) * 1000
                logger.exception(
                    "[REDSHIFT] Unexpected error fp=%s attempt=%s elapsed=%.2fms",
                    query_fingerprint,
                    attempt,
                    elapsed_ms,
                )
                print(f"❌ Error executing query: {e}")
                import traceback
                print(f"Traceback:\n{traceback.format_exc()}")
                if conn is not None:
                    try:
                        self.connection_pool.putconn(conn, close=True)
                    except Exception:
                        pass
                raise
        
        # All retries exhausted
        print(f"❌ All {max_attempts} attempts failed. Last error: {last_error}")
        raise RuntimeError(f"Redshift query failed after {max_attempts} attempts: {last_error}")
    
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
        
        Usa clasificación homologada con cortafuegos para evitar falsos positivos.
        
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
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # QUERY BASE con CTE para normalización
        query = f"""
        WITH base AS (
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
                
                /* Normalización 1 sola vez */
                TRIM(
                    REGEXP_REPLACE(
                        TRANSLATE(
                            LOWER(COALESCE(a.nombre,'') || ' ' || COALESCE(a.montaje,'')),
                            'áéíóúüñ',
                            'aeiouun'
                        ),
                        '[^a-z0-9]+',
                        ' '
                    )
                ) AS txt
                
            FROM tale.archivos a
            INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
            LEFT JOIN tale.clientes c ON pu.documento_cliente = c.documento
            WHERE a.entidad <> 'Unidad' AND {where_clause}
        )
        SELECT
            base.codigo_proforma,
            base.documento_cliente,
            base.nombre_cliente,
            base.codigo_proyecto,
            base.codigo_unidad,
            base.tipo_unidad,
            base.url,
            base.nombre_archivo,
            base.montaje,
            base.fecha_carga,
            
            CASE
                /* A) CORTAFUEGOS: bloquear falsos positivos antes de clasificar */
                WHEN REGEXP_INSTR(txt, '(^| )proforma( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )checklist( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )cuota(s)? inicial') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )cuota [123456]( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )(cuota_1|cuota_2|cuota_3|cuota_4)( |$)') > 0 THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )contrato( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )(separacion|separacion)( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )(cronograma|crono)( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )pago(s)?( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )compromiso( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )ahorro( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )correo( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )condicion(es)?( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )ahorro( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )formato( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )operacion( |$)') > 0
                THEN 'Otro'

                WHEN REGEXP_INSTR(txt, '(^| )(dj|djnp|djsbs|declaracion jurada)( |$)') > 0 THEN 'Otro'

                /* 1) MINUTA (incluye preminuta / pre minuta / MCV / minuta de compra venta) */
                WHEN
                    STRPOS(txt, 'minuta') > 0
                    OR STRPOS(txt, 'preminuta') > 0
                    OR STRPOS(txt, 'pre minuta') > 0
                    OR REGEXP_INSTR(txt, '(^| )mcv( |$)') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )minuta( |$)') > 0
                        AND REGEXP_INSTR(txt, '(^| )compra( |$)') > 0
                        AND REGEXP_INSTR(txt, '(^| )venta( |$)') > 0
                    )
                THEN 'Minuta'

                /* 2) ADENDA */
                WHEN
                    STRPOS(txt, 'adenda') > 0
                    OR STRPOS(txt, 'addenda') > 0
                    OR STRPOS(txt, 'addendum') > 0
                    OR STRPOS(txt, 'enmienda') > 0
                    OR STRPOS(txt, 'prorroga') > 0
                    OR STRPOS(txt, 'ampliacion') > 0
                    OR STRPOS(txt, 'modificac') > 0
                    OR STRPOS(txt, 'renuncia hipoteca') > 0
                THEN 'Adenda'

                /* 3) CARTA DE APROBACIÓN (incluye CA cuando va con contexto de aprobacion) */
                WHEN
                    (
                        STRPOS(txt, 'carta') > 0
                        AND REGEXP_INSTR(
                            txt,
                            '(^| )(aprob|preaprob|preacept|precal|credito|autoriz|conformidad|validac|approval|banco|bcp|ibk|interbank|bbva|scotia)( |$)'
                        ) > 0
                    )
                    OR REGEXP_INSTR(txt, '(^| )aprobacion( |$)') > 0
                    OR REGEXP_INSTR(txt, '(^| )aprobacion( |$).*(gerencia|banco)( |$)') > 0
                    OR REGEXP_INSTR(txt, '(^| )correo( |$).*aprob') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )ca( |$)') > 0
                        AND REGEXP_INSTR(txt, '(aprob|preacept|banco|validac|conformidad)') > 0
                    )
                    OR REGEXP_INSTR(txt, '(^| )carta( |$).*aprobacion') > 0
                THEN 'Carta de Aprobación'

                /* 4) VOUCHER (señales fuertes + nuevas etiquetas con contexto) */
                WHEN
                    STRPOS(txt, 'voucher') > 0
                    OR STRPOS(txt, 'vaucher') > 0
                    OR REGEXP_INSTR(txt, '(^| )vou( |$)') > 0
                    OR STRPOS(txt, 'comprobante') > 0
                    OR STRPOS(txt, 'recibo') > 0
                    OR STRPOS(txt, 'transfer') > 0
                    OR STRPOS(txt, 'transf') > 0
                    OR STRPOS(txt, 'deposit') > 0
                    OR STRPOS(txt, 'operacion') > 0
                    OR STRPOS(txt, 'interbanc') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )vs( |$)') > 0
                        AND (
                            STRPOS(txt, 'voucher') > 0
                            OR REGEXP_INSTR(txt, '(^| )(separacion|sep)( |$)') > 0
                        )
                    )
                    OR (
                        STRPOS(txt, 'voucher') > 0
                        AND REGEXP_INSTR(txt, '(^| )(separacion|sep)( |$)') > 0
                    )
                    OR (
                        STRPOS(txt, 'constancia') > 0
                        AND REGEXP_INSTR(txt, '(^| )(transfer|transf|pago|abono|deposit|operacion)( |$)') > 0
                    )
                THEN 'Voucher'

                /* 5) VOUCHER (señal débil: "pago" pero ya bloqueamos cronogramas arriba) */
                WHEN REGEXP_INSTR(txt, '(^| )pago(s)?( |$)') > 0
                THEN 'Voucher'

                ELSE 'Otro'
            END AS tipo_documento
            
        FROM base
        ORDER BY base.fecha_carga DESC
        LIMIT {limit} OFFSET {offset}
        """
        
        # FILTRO POR TIPOS (si se proporciona)
        # Aplicar DESPUÉS del CASE mediante subconsulta
        if document_types and len(document_types) > 0:
            # Crear lista de placeholders para IN clause
            placeholders = ','.join(['%s'] * len(document_types))
            query = f"""
            SELECT * FROM (
                {query}
            ) AS classified
            WHERE tipo_documento IN ({placeholders})
            """
            params_list.extend(document_types)
        
        # Convert to tuple
        params = tuple(params_list) if params_list else None
        
        result = self.execute_query(query, params)
        return result
    
    def get_document_by_codigo(self, codigo_proforma: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento específico por código de proforma con clasificación homologada"""
        query = """
        WITH base AS (
            SELECT
                a.codigo_proforma,
                pu.documento_cliente,
                c.nombres || ' ' || c.apellidos AS nombre_cliente,
                pu.codigo_proyecto,
                pu.codigo_unidad,
                /* HOMOLOGACIÓN CANÓNICA tipo_unidad - Prioridad: LC > DPTO > EST > DEP > GAB > OTRO */
                CASE
                    WHEN pu.tipo_unidad IS NULL OR TRIM(pu.tipo_unidad) = '' THEN 'SIN_DATA'
                    WHEN LOWER(pu.tipo_unidad) LIKE '%%local comercial%%' THEN 'LC'
                    WHEN LOWER(pu.tipo_unidad) LIKE '%%departamento%%' THEN 'DPTO'
                    WHEN LOWER(pu.tipo_unidad) LIKE '%%estacionamiento%%' THEN 'EST'
                    WHEN LOWER(pu.tipo_unidad) LIKE '%%depósito%%' OR 
                         LOWER(pu.tipo_unidad) LIKE '%%deposito%%' THEN 'DEP'
                    WHEN LOWER(pu.tipo_unidad) LIKE '%%gabinete%%' THEN 'GAB'
                    ELSE 'OTRO'
                END AS tipo_unidad,
                a.url,
                a.nombre as nombre_archivo,
                a.montaje,
                TO_CHAR(a.fecha_carga, 'YYYY-MM-DD HH24:MI:SS') as fecha_carga,
                
                /* Normalización 1 sola vez */
                TRIM(
                    REGEXP_REPLACE(
                        TRANSLATE(
                            LOWER(COALESCE(a.nombre,'') || ' ' || COALESCE(a.montaje,'')),
                            'áéíóúüñ',
                            'aeiouun'
                        ),
                        '[^a-z0-9]+',
                        ' '
                    )
                ) AS txt
                
            FROM tale.archivos a
            INNER JOIN tale.proforma_unidad pu ON a.codigo_proforma = pu.codigo_proforma
            LEFT JOIN tale.clientes c ON pu.documento_cliente = c.documento
            WHERE a.codigo_proforma = %s
        )
        SELECT
            base.codigo_proforma,
            base.documento_cliente,
            base.nombre_cliente,
            base.codigo_proyecto,
            base.codigo_unidad,
            base.tipo_unidad,
            base.url,
            base.nombre_archivo,
            base.montaje,
            base.fecha_carga,
            
            CASE
                /* A) CORTAFUEGOS: bloquear falsos positivos antes de clasificar */
                WHEN REGEXP_INSTR(txt, '(^| )proforma( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )checklist( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )cuota(s)? inicial') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )cuota [123456]( |$)') > 0 THEN 'Otro'
                WHEN REGEXP_INSTR(txt, '(^| )(cuota_1|cuota_2|cuota_3|cuota_4)( |$)') > 0 THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )contrato( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )(separacion|separacion)( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )(cronograma|crono)( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )pago(s)?( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )compromiso( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )ahorro( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )correo( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )condicion(es)?( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )ahorro( |$)') > 0
                THEN 'Otro'

                WHEN
                    REGEXP_INSTR(txt, '(^| )formato( |$)') > 0
                    AND REGEXP_INSTR(txt, '(^| )operacion( |$)') > 0
                THEN 'Otro'

                WHEN REGEXP_INSTR(txt, '(^| )(dj|djnp|djsbs|declaracion jurada)( |$)') > 0 THEN 'Otro'

                /* 1) MINUTA */
                WHEN
                    STRPOS(txt, 'minuta') > 0
                    OR STRPOS(txt, 'preminuta') > 0
                    OR STRPOS(txt, 'pre minuta') > 0
                    OR REGEXP_INSTR(txt, '(^| )mcv( |$)') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )minuta( |$)') > 0
                        AND REGEXP_INSTR(txt, '(^| )compra( |$)') > 0
                        AND REGEXP_INSTR(txt, '(^| )venta( |$)') > 0
                    )
                THEN 'Minuta'

                /* 2) ADENDA */
                WHEN
                    STRPOS(txt, 'adenda') > 0
                    OR STRPOS(txt, 'addenda') > 0
                    OR STRPOS(txt, 'addendum') > 0
                    OR STRPOS(txt, 'enmienda') > 0
                    OR STRPOS(txt, 'prorroga') > 0
                    OR STRPOS(txt, 'ampliacion') > 0
                    OR STRPOS(txt, 'modificac') > 0
                    OR STRPOS(txt, 'renuncia hipoteca') > 0
                THEN 'Adenda'

                /* 3) CARTA DE APROBACIÓN */
                WHEN
                    (
                        STRPOS(txt, 'carta') > 0
                        AND REGEXP_INSTR(
                            txt,
                            '(^| )(aprob|preaprob|preacept|precal|credito|autoriz|conformidad|validac|approval|banco|bcp|ibk|interbank|bbva|scotia)( |$)'
                        ) > 0
                    )
                    OR REGEXP_INSTR(txt, '(^| )aprobacion( |$)') > 0
                    OR REGEXP_INSTR(txt, '(^| )aprobacion( |$).*(gerencia|banco)( |$)') > 0
                    OR REGEXP_INSTR(txt, '(^| )correo( |$).*aprob') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )ca( |$)') > 0
                        AND REGEXP_INSTR(txt, '(aprob|preacept|banco|validac|conformidad)') > 0
                    )
                    OR REGEXP_INSTR(txt, '(^| )carta( |$).*aprobacion') > 0
                THEN 'Carta de Aprobación'

                /* 4) VOUCHER (señales fuertes + nuevas etiquetas con contexto) */
                WHEN
                    STRPOS(txt, 'voucher') > 0
                    OR STRPOS(txt, 'vaucher') > 0
                    OR REGEXP_INSTR(txt, '(^| )vou( |$)') > 0
                    OR STRPOS(txt, 'comprobante') > 0
                    OR STRPOS(txt, 'recibo') > 0
                    OR STRPOS(txt, 'transfer') > 0
                    OR STRPOS(txt, 'transf') > 0
                    OR STRPOS(txt, 'deposit') > 0
                    OR STRPOS(txt, 'operacion') > 0
                    OR STRPOS(txt, 'interbanc') > 0
                    OR (
                        REGEXP_INSTR(txt, '(^| )vs( |$)') > 0
                        AND (
                            STRPOS(txt, 'voucher') > 0
                            OR REGEXP_INSTR(txt, '(^| )(separacion|sep)( |$)') > 0
                        )
                    )
                    OR (
                        STRPOS(txt, 'voucher') > 0
                        AND REGEXP_INSTR(txt, '(^| )(separacion|sep)( |$)') > 0
                    )
                    OR (
                        STRPOS(txt, 'constancia') > 0
                        AND REGEXP_INSTR(txt, '(^| )(transfer|transf|pago|abono|deposit|operacion)( |$)') > 0
                    )
                THEN 'Voucher'

                /* 5) VOUCHER (señal débil) */
                WHEN REGEXP_INSTR(txt, '(^| )pago(s)?( |$)') > 0
                THEN 'Voucher'

                ELSE 'Otro'
            END AS tipo_documento
            
        FROM base
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
        """Prueba la conexión a Redshift, intentando re-inicializar si falla."""
        # Try to ensure pool exists
        try:
            self._ensure_pool()
        except RuntimeError:
            return False
        try:
            self.execute_query("SELECT 1 as test")
            return True
        except Exception:
            # Attempt one more re-init
            try:
                self._reinitialize_pool()
                if self.connection_pool is None:
                    return False
                self.execute_query("SELECT 1 as test")
                return True
            except Exception:
                return False
    
    def close(self):
        """Cierra el connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            print("✅ Redshift connection pool closed")

redshift_service = RedshiftService()
