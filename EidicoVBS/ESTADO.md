# Estado del proyecto EidicoVBS

Última actualización: 2026-11-16

## Scripts actuales

### `EIDICO.vbs`
- **Función:** Lanzador y actualizador automático de Eidico.
  - Verifica que el ejecutable exista en la ruta de red (`\\172.31.11.146\Fileserver\EidicoPrueba\EidicoPrueba.Exe`).
  - Si no existe en la carpeta local (`C:\Program Files (x86)\Sol Sistemas\Eidico\`), copia todos los archivos desde el servidor.
  - Si ya existe localmente, compara tamaño y versión (`VersionMenorQue`); si difieren, cierra procesos abiertos (`CerrarSiEstaAbierto` vía WMI + `taskkill`) previa confirmación del usuario y actualiza los archivos.
  - Verifica integridad por tamaño antes de ejecutar el binario local.
- **Estado:** Implementado y funcional para entorno de pruebas (`EidicoPrueba`). Pendiente apuntar a las rutas/ejecutable de producción si corresponde.

### `EIDICO_test.vbs`
- **Función:** Copia de pruebas de `EIDICO.vbs` que fuerza la rama de actualización (`If True Then` en la línea 29) para testear el flujo de cierre de proceso y copiado sin depender de diferencias de versión o tamaño.
- **Estado:** Script de prueba únicamente (no apto para producción).

## Pendientes y próximos pasos

- Confirmar si `EIDICO.vbs` debe apuntar al ejecutable y carpeta de producción (en lugar de `EidicoPrueba.Exe` y `\\172.31.11.146\Fileserver\EidicoPrueba\`).
- Verificar que todos los archivos `.vbs` se mantengan guardados en codificación Windows-1252 (ANSI).
- Validar con el usuario antes de ejecutar cualquier prueba de `EIDICO_test.vbs`.
