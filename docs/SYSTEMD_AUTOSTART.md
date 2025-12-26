# Configuración de Auto-Inicio del Contenedor (Systemd)

## Descripción

El contenedor `tale-download` está configurado para iniciarse automáticamente cuando el servidor se reinicia, utilizando un servicio `systemd` del usuario.

## 📋 Cómo Funciona

### Servicio Systemd

El archivo `/home/tale_cons_srv/.config/systemd/user/container-tale-download.service` contiene la configuración para:

1. **Iniciar automáticamente** el contenedor al reiniciar
2. **Reintentar automáticamente** si el contenedor falla (`Restart=always`)
3. **Limpiar recursos** cuando se detiene (`--rm`)
4. **Mapear el puerto 8010** para acceso externo
5. **Cargar variables de entorno** desde `.env`

### Configuración del Servicio

```ini
[Unit]
Description=Podman container-tale-download.service
Wants=network-online.target
After=network-online.target

[Service]
Restart=always
TimeoutStopSec=70
# Inicia el contenedor con configuración completa
ExecStart=/usr/bin/podman run ...

[Install]
WantedBy=default.target
```

## 🚀 Comandos Útiles

### Ver estado del servicio
```bash
systemctl --user status container-tale-download.service
```

### Ver logs del servicio
```bash
journalctl --user -u container-tale-download.service -f
```

### Reiniciar el servicio
```bash
systemctl --user restart container-tale-download.service
```

### Detener el servicio
```bash
systemctl --user stop container-tale-download.service
```

### Ver si está habilitado para auto-inicio
```bash
systemctl --user is-enabled container-tale-download.service
```

### Listar todos los servicios de usuario
```bash
systemctl --user list-units --type=service
```

## 📦 Ubicación de Archivos

- **Servicio**: `/home/tale_cons_srv/.config/systemd/user/container-tale-download.service`
- **Variables de entorno**: `/home/tale_cons_srv/projects/tale-download/.env`
- **Imagen Docker**: `localhost/tale-download:latest` (en Podman)

## ✅ Verificación

### Verificar que el servicio está activo
```bash
podman ps -a | grep tale-download
```

### Verificar que responde
```bash
curl http://localhost:8010/api/health
```

## 🔄 Flujo de Arranque

1. **Server se reinicia**
2. **systemd inicia sesión de usuario**
3. **Servicio `container-tale-download.service` se ejecuta**
4. **Podman lanza el contenedor con:**
   - Imagen: `localhost/tale-download:latest`
   - Puerto: `8010:8010`
   - Variables de entorno desde `.env`
5. **Contenedor ejecuta FastAPI en puerto 8010**
6. **Frontend disponible en**: `http://localhost:8010`

## 🛠️ Equivalencia con TalePlanHub

Este servicio utiliza la misma configuración que `taleplanhub`:

```bash
# Ver configuración de taleplanhub
cat ~/.config/systemd/user/container-taleplanhub.service

# Ver estado de taleplanhub
systemctl --user status container-taleplanhub.service
```

## ⚠️ Notas Importantes

1. **El servicio es de usuario** (no root):
   - Solo se inicia si el usuario `tale_cons_srv` tiene una sesión activa
   - O si está habilitado el "lingering" del usuario

2. **Habilitar lingering** (opcional, para inicio sin sesión):
   ```bash
   loginctl enable-linger tale_cons_srv
   ```

3. **El archivo `.env` debe existir** en:
   ```
   /home/tale_cons_srv/projects/tale-download/.env
   ```

4. **Política de reinicio**:
   - `Restart=always`: Reinicia siempre si falla
   - `TimeoutStopSec=70`: Espera 70 segundos antes de forzar detención

## 📝 Cambios Realizados

- **Creación del archivo de servicio**: `container-tale-download.service`
- **Habilitación automática**: `systemctl --user enable`
- **Inicio del servicio**: `systemctl --user start`
- **Verificación**: Servicio activo y contenedor respondiendo

## 🎯 Próximos Pasos

Si deseas que el contenedor se inicie incluso sin sesión activa del usuario:

```bash
sudo loginctl enable-linger tale_cons_srv
```

---

**Creado**: 2025-12-23 15:21 UTC-5  
**Equivalente a**: `container-taleplanhub.service`  
**Estado**: ✅ Activo y funcionando
