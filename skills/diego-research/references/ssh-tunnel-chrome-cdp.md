# SSH Tunnel + Chrome CDP — Session Log

**Fecha:** 2026-05-11
**Objetivo:** Conectar Hermes Agent (server 46.225.73.40) al Chrome local de Diego via CDP/SSH tunnel para automatización de browser con firma digital.

## Topología

```
Diego (Chrome con --remote-debugging-port=9222)
    └── SSH reverse tunnel (-R)
            └── Hermes server (46.225.73.40:9222 → localhost:9222 de Diego)
```

## Comandos clave

### En la máquina de Diego (cliente SSH)
```bash
# Chrome con debugging
google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.hermes/chrome-debug

# SSH reverse tunnel (desde la máquina de Diego hacia el server)
ssh -R 0.0.0.0:9222:localhost:9222 root@46.225.73.40
```

### En el server (46.225.73.40)
```bash
# Ver si el tunnel está escuchando
ss -tlnp | grep 9222

# Test de conexión CDP
curl http://localhost:9222/json/version
```

## Errores encontrados

### Error 1: "remote port forwarding failed for listen port 9222"
**Causa:** Algo estaba ocupando el puerto 9222 en el server (o sshd lo rechazaba).

**Solución intentada:** Cambiar a puerto 9999 — pero el problema persistió.

### Error 2: Tunnel establecido pero sin binding en 0.0.0.0
**Síntoma:** `ss -tlnp` mostraba `127.0.0.1:9222` en vez de `0.0.0.0:9222` después de reconnect.

**Causa:** `GatewayPorts yes` en sshd_config no se estaba aplicando correctamente. El sshd instance viejo no había levantado la nueva config.

**Solución:** `systemctl restart ssh` en el server.

### Error 3: AllowTcpForwarding
**Configuración:** `#AllowTcpForwarding yes` (comentado = default yes)
**Veredicto:** No era el problema.

### Error 4: AppArmor
**Verificado:** sshd no estaba restringido por AppArmor (0 profiles in enforce mode para sshd).

## Configuración SSH server (/etc/ssh/sshd_config)
```
GatewayPorts yes
AllowTcpForwarding yes  # descomentar paraClar
PermitRootLogin yes
```

## Estado final
**NO RESUELTO** — El tunnel SSH sigue sin bindear correctamente a 0.0.0.0. El sshd en este server (KVM container) pareciera tener restricciones de kernel o namespace que impiden el TCP forwarding reverso.

## Alternativas probadas/sugeridas

1. **SSH local forward (-L):** No aplicable porque Hermes no puede iniciar conexiones salientes hacia Diego.
2. **Docker en máquina de Diego:** Chrome en container, expuesto via HTTP — más predecible que SSH tunnel.
3. **ngrok o similar:** Exponer puerto local 9222 via tunnel público.
4. **Browser remoto via API:** Si el objetivo es solo navegación automatizada, considerar Selenium/Playwright en la máquina de Diego controlado por comandos.

## Notas para下次
- `ss -tlnp | grep PORT` para verificar listening ports
- `tail /var/log/auth.log | grep sshd` para ver intentos de conexión
- `systemctl restart ssh` no siempre alcanza — puede requerir reiniciar el proceso sshd directamente
- Si `-R` falla con "port forwarding failed", el problema está en el server, no en el cliente
- En contenedores KVM/VM, el TCP forwarding puede estar restringido a nivel hypervisor
