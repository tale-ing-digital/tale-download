import os
import psycopg2

# Configurar variables de entorno
os.environ['REDSHIFT_HOST'] = 'rssperant-enoc.cmd1cn2chqlh.us-east-1.redshift.amazonaws.com'
os.environ['REDSHIFT_PORT'] = '5439'
os.environ['REDSHIFT_DATABASE'] = 'cb1db7e6641b'
os.environ['REDSHIFT_USER'] = 'a66u3a72rjxb'
os.environ['REDSHIFT_PASSWORD'] = 'i55xG33xiQ84=='

try:
    # Conectar a Redshift
    conn = psycopg2.connect(
        host=os.environ['REDSHIFT_HOST'],
        port=int(os.environ['REDSHIFT_PORT']),
        database=os.environ['REDSHIFT_DATABASE'],
        user=os.environ['REDSHIFT_USER'],
        password=os.environ['REDSHIFT_PASSWORD']
    )
    
    cursor = conn.cursor()
    
    # Consultar una fila de ejemplo
    cursor.execute("SELECT * FROM tale.archivos LIMIT 1")
    
    # Obtener nombres de columnas
    columns = [desc[0] for desc in cursor.description]
    
    print("\n=== COLUMNAS DE LA TABLA tale.archivos ===")
    for i, col in enumerate(columns, 1):
        print(f"{i}. {col}")
    
    # Obtener los datos de la fila de ejemplo
    row = cursor.fetchone()
    if row:
        print("\n=== EJEMPLO DE DATOS ===")
        for col, value in zip(columns, row):
            print(f"{col}: {value}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
