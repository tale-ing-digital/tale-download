# Fix: Systemd Type=notify → Type=simple

**Problema**: Contenedor no se auto-iniciaba en reinicio de servidor
**Causa**: `Type=notify` causaba timeout de systemd esperando señal READY=1
**Solución**: Cambiar a `Type=simple` en `/home/tale_cons_srv/.config/systemd/user/container-tale-download.service`
**Resultado**: Auto-inicio funciona correctamente

```diff
- Type=notify
+ Type=simple
```

Aplicado: 2025-12-23 16:45 UTC-5
