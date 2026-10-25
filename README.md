# Guilliman — Sistema Integrado de Gestión de Expedientes Penales

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](COPYING)
[![Python 3.12 (32-bit)](https://img.shields.io/badge/Python-3.12%20(32--bit)-green.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15-blue.svg)](https://riverbankcomputing.com/software/pyqt/)

Aplicación de escritorio nativa para Windows diseñada para la gestión integral de expedientes penales en circuitos judiciales. Permite registrar y dar seguimiento a causas judiciales, las partes involucradas, audiencias programadas y generar reportes en PDF.

> **100 % offline** — No requiere servidor, conexión a internet ni instalación de Python.

---

## Funcionalidades

- **Panel de inicio** — Contadores de expedientes, audiencias próximas (7 días) y
  audiencias pendientes de audio o acta; tabla de las próximas audiencias.
- **Gestión de expedientes** — Número de expediente único, fiscalía, fiscal, defensa, agencia aprehendadora, descripción del hecho, resumen, tipo de origen, estado de fallo y fechas procesales.
- **Archivado y restauración** — Los expedientes se archivan (no se borran) y pueden
  restaurarse; el borrado definitivo queda como acción explícita sobre un archivado.
- **Partes por expediente** (borrado en cascada al eliminar el expediente):
  - **Acusados** — Nombre, cédula, fecha de aprehensión, fecha de audiencia, dirección, teléfono y notas.
  - **Víctimas y testigos** — Nombre, cédula, dirección, teléfono y notas.
  - **Peritos** — Nombre, comparecencia y fecha.
  - **Pruebas documentales** — Nombre, estado (en posesión / evacuada) con fechas.
- **Agenda de audiencias** — Calendario con tipo, estado y notas por audiencia; filtro
  por fecha y estado. Exportable a PDF y a iCalendar (`.ics`) con recordatorio 1 día antes
  para importar en Outlook/Google Calendar.
- **Búsqueda instantánea** — Por número, MP, descripción, hechos y ubicación, con filtros
  de estado, veredicto, tipo de delito, nombres, rango de fechas y procedencia. Se aplica
  mientras se escribe, recuerda los filtros entre sesiones y permite ordenar por columna.
- **Audios de audiencias** — Adjunta la grabación de cada audiencia; el archivo se copia
  al equipo local para no depender del teléfono. Permite abrir/reproducir el audio desde
  el detalle del expediente.
- **Acta por audiencia** — Redacta o pega la transcripción de cada audiencia (con
  autoguardado) y expórtala a PDF (para imprimir), RTF (editable en Word) o imprímela
  directamente. La tabla de audiencias indica cuáles ya tienen acta.
- **Duplicar audiencia** — Copia tipo y notas y la reprograma 7 días después, para las
  continuaciones.
- **Búsqueda de expedientes** — Por número, fiscalía u otros criterios.
- **Exportación a PDF** — Del expediente individual y de la agenda completa (reportlab).
- **Respaldo completo** — Un solo `.zip` con la base de datos y todos los audios (Ajustes).
  El "Respaldo rápido" rota automáticamente y conserva los últimos 10.
- **Verificación de audios** — Detecta audios referenciados que faltan en disco o que
  apuntan fuera del almacén local (Ajustes → "Verificar audios").
- **Tema claro / oscuro** — Persistente entre sesiones (sección Ajustes). La ventana
  recuerda su tamaño y si estaba maximizada.
- **Normalización automática** — Campos de entrada en MAYÚSCULAS.

---

## Arquitectura

```
Guilliman/
├── db/               # Lógica de negocio + persistencia
│   ├── services/     #   Mixins por entidad (case_files, defendants, victims…)
│   ├── models.py     #   Modelos ORM (SQLAlchemy 2.0)
│   ├── schemas.py    #   Validación con pydantic
│   ├── service.py    #   CaseFileService (API pública compuesta)
│   └── database.py   #   Engine, session factory, resolución de rutas
├── ui/               # Interfaz PyQt5 / qfluentwidgets
│   ├── case_detail_view/  #   Sub-vistas del detalle de expediente
│   ├── dialogs/      #   Diálogos por entidad
│   ├── exporters.py  #   Exportador PDF (sin dependencia PyQt)
│   └── app_shell.py  #   FluentWindow principal
├── main.py           # Punto de entrada
├── tests/            # Suite de pruebas (pytest)
├── build.bat         # Empaquetado con PyInstaller (32 bits)
└── requirements.txt  # Dependencias (versiones fijadas)
```

**Regla de arquitectura:** La UI importa **solo** desde `db` (re-exportado en `db/__init__.py`), nunca desde `db.database` ni los modelos ORM directamente.

---

## Inicio rápido (desarrollo)

### Requisitos

- Python 3.12 (desarrollo: 64 o 32 bits; empaquetado: **solo 32 bits**)
- Dependencias listadas en `requirements.txt`

### Instalación y ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar la aplicación
python main.py
```

Se abre la ventana principal con las secciones **Expedientes**, **Nuevo**, **Agenda** y **Ajustes**.

### Pruebas

```bash
python -m pytest tests
```

Las pruebas que usan PyQt corren de forma headless (`QT_QPA_PLATFORM=offscreen`).

---

## Empaquetado para Windows de 32 bits

El público objetivo son PCs de 32 bits, por lo que el build se hace exclusivamente para esa arquitectura.

```bash
# Opción por defecto (py launcher con Python 3.12 de 32 bits)
build.bat

# Opción con intérprete explícito
build.bat python312\python.exe
```

**Resultado:** `dist\Guilliman\Guilliman.exe` — ejecutable auto-suficiente que no requiere Python ni conexión a internet.

### Distribución

Copia la carpeta `dist\Guilliman` a la PC destino y ejecuta `Guilliman.exe`.

> **Nota técnica:** SQLAlchemy 2.0 declara `greenlet`, pero greenlet no publica wheel de 32 bits. Como la app es 100 % sincrona, `build.bat` instala SQLAlchemy con `--no-deps`. No compilar con Python 3.13 de 32 bits.

---

## Datos y configuración

La base de datos (`case_files.db`), la configuración (`settings.json`) y los audios de
audiencias se resuelven con esta precedencia:

| Prioridad | Fuente | Descripción |
|-----------|--------|-------------|
| 1 | `Guilliman_DATA_DIR` | Variable de entorno (ruta explícita; útil para pruebas o despliegues portátiles) |
| 2 | Modo congelado (exe) | `%LOCALAPPDATA%\Guilliman` en Windows (`~/.guilliman` en otros SO) |
| 3 | Modo desarrollo | Raíz del proyecto (`case_files.db`, `settings.json` y `audios/` en `.gitignore`) |

Estructura del directorio de datos:

```
<data_dir>/
├── case_files.db       # base de datos SQLite
├── settings.json       # preferencias (tema)
├── audios/             # copias locales de los audios de audiencias (.gitignore)
└── backups/            # respaldos generados automáticamente
```

Los audios se guardan con un nombre único y la base de datos solo almacena su ruta
relativa. Al reemplazar o quitar un audio, borrar una audiencia o eliminar el expediente,
el archivo correspondiente se elimina del store.

### Respaldo

En **Ajustes → Respaldar datos...** se genera un único archivo `.zip` con la base de
datos y toda la carpeta `audios/`. **Restaurar datos** reemplaza ambos; antes de
restaurar, la app crea automáticamente un respaldo de seguridad.

**Respaldo rápido** guarda en `<data_dir>/backups/` y rota, conservando los últimos 10
respaldos. El panel de inicio muestra la antigüedad del último respaldo y avisa cuando
conviene hacer uno nuevo.

**Verificar audios** recorre las audiencias y reporta archivos faltantes o rutas fuera
del almacén local.

---

## Solución de problemas

| Síntoma | Causa / Solución |
|---------|------------------|
| `No module named greenlet` al compilar | Se usó Python 3.13 de 32 bits o `pip install -r requirements.txt` en 32 bits. Usa `build.bat` (instala SQLAlchemy sin greenlet). |
| La ventana no aparece tras el build | Ejecuta `dist\Guilliman\Guilliman.exe` desde una consola para ver errores. Verifica que se copió toda la carpeta. |
| `py` no encuentra 3.12-32 | Instala Python 3.12 (x86/32-bit) desde python.org con el "py launcher" habilitado. |
| Error "No se pudo inicializar la base de datos" | Revisa permisos de escritura en la carpeta de datos (ver tabla anterior). |
| "El archivo de audio no se encuentra en este equipo" | Se restauró un `.db` sin su carpeta `audios/`, o el archivo se movió/borró manualmente. Restaura un respaldo completo (`.zip`) o vuelve a adjuntar el audio. |
| Texto en minúsculas inesperado | El proyecto normaliza los campos a MAYÚSCULAS en la capa UI (`ui/shared`). No es un bug. |

---

## Licencia

Este proyecto está licenciado bajo la [Apache License 2.0](COPYING).

```
Copyright 2024 Guilliman — Circuito Judicial Penal

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```
