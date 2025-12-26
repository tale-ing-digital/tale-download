# 🚀 TaleDownload v2.0.0 - Quick Reference

## 📊 Estado Actual

| Componente | Estado | Puerto | Servicio |
|-----------|--------|--------|----------|
| **API Backend** | ✅ Healthy | 8010 | `container-tale-download.service` |
| **Frontend** | ✅ Running | 8010 | Servido por Vite |
| **Database** | ✅ Redshift | Remote | AWS Read-Only |
| **Auto-restart** | ✅ Enabled | — | systemd user service |

## 🔧 Acceso Rápido

### Ver status de la aplicación
```bash
# Estado del servicio
systemctl --user status container-tale-download.service

# Logs en tiempo real
podman logs -f tale-download

# Health check
curl http://localhost:8010/api/health
```

### Reiniciar la aplicación
```bash
systemctl --user restart container-tale-download.service
```

### Detener la aplicación
```bash
systemctl --user stop container-tale-download.service
```

### Recompilar e instalar
```bash
cd /home/tale_cons_srv/projects/tale-download
./deploy.sh --no-cache
```

## 📈 Versión Actual

- **v2.0.0** - Released 2025-12-23 14:48 UTC-5
- **Cambios principales**:
  - ✅ Fixed: 348 image conversion errors (ImageReader fix)
  - ✅ Fixed: Port conflict with PGAdmin (8080 → 8010)
  - ✅ Feat: Folder names in MAYÚSCULAS (uppercase)
  - ✅ Feat: Port parametrizable via ENV

## 📂 Estructura de Carpetas

```
/home/tale_cons_srv/projects/tale-download/
├── backend/                 # FastAPI + Uvicorn
│   ├── main.py             # Entry point (PORT env var configurable)
│   ├── api/                # REST endpoints
│   ├── services/           # PDF, ZIP, Download services
│   ├── utils/              # file_naming, helpers
│   └── tests/              # Validation tests (4/4 passing)
├── client/                 # React + Vite frontend
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Page components
│       └── lib/            # API client
├── deploy.sh               # Deployment script (no-cache option)
├── CHANGELOG.md            # Release notes
├── SYSTEMD_AUTOSTART.md    # Systemd configuration docs
└── .env                    # Environment variables
```

## 🛠️ Configuración de Variables de Entorno

Archivo: `/home/tale_cons_srv/projects/tale-download/.env`

```env
# Puerto de la aplicación
PORT=8010

# Configuración de Redshift (si está configurada)
REDSHIFT_HOST=...
REDSHIFT_USER=...
REDSHIFT_PASSWORD=...
REDSHIFT_DATABASE=...

# Otras variables según sea necesario
```

## 🚀 Auto-reinicio en Reboot del Servidor

El contenedor se reinicia automáticamente cuando:
1. El servidor se reinicia
2. El contenedor falla
3. El sistema se recupera de un error

**Configuración**: `container-tale-download.service` con `Restart=always`

Para verificar:
```bash
systemctl --user is-enabled container-tale-download.service
# Output: enabled
```

## 📦 Contenedor Docker

**Imagen**: `localhost/tale-download:latest`

**Multi-stage build**:
1. Stage 1: Node.js builder (compila React frontend)
2. Stage 2: Python runtime (ejecuta FastAPI backend)

**Exposiciones**:
- Puerto 8010 (HTTP)
- Health check cada 30s en `/api/health`

## 🧪 Tests

```bash
# Ejecutar suite de validación
cd /home/tale_cons_srv/projects/tale-download
python -m pytest backend/tests/test_reprocess.py -v

# Resultado esperado: 4/4 passing ✅
```

## 📝 Logs Importantes

### En caso de problemas

```bash
# Ver logs del servicio systemd
journalctl --user -u container-tale-download.service -f

# Ver logs del contenedor
podman logs -f tale-download

# Ver output de stderr
podman logs tale-download 2>&1 | tail -50

# Listar contenedores activos
podman ps -a | grep tale-download
```

## 🔍 Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| Contenedor no inicia | `systemctl --user status container-tale-download.service` |
| Puerto en uso | Cambiar `PORT=8010` en `.env` |
| API no responde | `curl http://localhost:8010/api/health` |
| Frontend no carga | Verificar `vite.config.ts` proxy a `localhost:8010` |
| Archivos no procesan | Ejecutar tests: `pytest backend/tests/test_reprocess.py` |

## 🎯 Roadmap (Próximas Mejoras)

- [ ] Añadir autenticación JWT
- [ ] Cacheo de descargas
- [ ] Monitoreo centralizado
- [ ] Dashboard de estadísticas
- [ ] Rate limiting

## 📚 Documentación Relacionada

- [CHANGELOG.md](CHANGELOG.md) - Historial de cambios
- [SYSTEMD_AUTOSTART.md](SYSTEMD_AUTOSTART.md) - Configuración de systemd
- [README.md](README.md) - Documentación principal
- [docs/](docs/) - Análisis y decisiones técnicas

## 👤 Contacto & Soporte

Para reportar problemas o sugerencias, consultar con el equipo de desarrollo.

---

**Última actualización**: 2025-12-23 15:30 UTC-5  
**Versión**: v2.0.0  
**Estado del Sistema**: ✅ Producción Ready
