# ChokeHound - Analizador de Choke Points con BloodHound CE

[English](#chokehound---bloodhound-choke-points-analyzer) | [Español](#chokehound---analizador-de-puntos-de-estrangulamiento-de-bloodhound)

---

## ChokeHound - Analizador Choke Points con BloodHound CE

ChokeHound es una herramienta de análisis de seguridad que identifica Choke Points (puntos de estrangulamiento) críticos en Active Directory utilizando datos recopilados por BloodHound CE. Los Choke Points son relaciones de privilegio críticas que conectan objetos no Tier-0 con objetos Tier-0, representando ubicaciones óptimas para bloquear el mayor número de rutas de ataque.

### Características

- **Identificación de Choke Points**: Encuentra relaciones directas entre objetos no Tier-0 y objetos Tier-0
- **Priorización por riesgo**: Calcula una puntuación de riesgo para cada punto de estrangulamiento basada en múltiples factores
- **Análisis de rutas de ataque**: Identifica cuántas rutas de ataque se ven afectadas por cada punto de estrangulamiento
- **Informes en Excel**: Genera informes detallados en formato Excel con múltiples hojas de cálculo
- **Log de cálculos de riesgo**: Opción para generar un archivo de log detallado explicando los cálculos de riesgo

### Requisitos Previos

- Python 3.7 o superior
- Neo4j (versión 4.x o superior recomendada)
- BloodHound con datos importados en Neo4j
- Acceso a la base de datos Neo4j de BloodHound

### Requisitos antes de la ejecución

1. **Instalación de BloodHound CE**: Despliega BloodHound Community Edition y asegúrate de que el backend de Neo4j esté inicializado y accesible mediante credenciales válidas.
2. **Recolección de datos con SharpHound o AzureHound**: Ejecuta los recopiladores oficiales (SharpHound para entornos on-prem o AzureHound para Azure AD) y carga los resultados en BloodHound CE para poblar la base de datos.
3. **Configuración de Tier 0 en BloodHound**: Etiqueta correctamente los objetos críticos con `Tag_Tier_Zero` (nodos, grupos, cuentas y equipos Tier-0). ChokeHound depende de esta clasificación para identificar los puntos de estrangulamiento.

### Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/ChokeHound.git
   cd ChokeHound/Script
   ```

2. **Instalar dependencias de Python**:
   ```bash
   pip install py2neo pandas openpyxl
   ```
   
   O crear un archivo `requirements.txt` con el siguiente contenido:
   ```
   py2neo>=2021.2.3
   pandas>=1.3.0
   openpyxl>=3.0.9
   ```
   
   Y luego instalar:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verificar que Neo4j esté ejecutándose**:
   Asegúrate de que tu instancia de Neo4j con los datos de BloodHound esté ejecutándose y accesible.

### Configuración

Edita el archivo `config.py` para configurar la conexión a Neo4j:

```python
# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "bloodhoundcommunityedition"

# Default output filename
DEFAULT_OUTPUT_FILENAME = "ChokeHound_report.xlsx"

# Limit for "Prioritise choke points" query
LIMIT_CHOKE_POINTS = 200
```

**Parámetros de configuración**:
- `NEO4J_URI`: URI de conexión a Neo4j (por defecto: `bolt://localhost:7687`)
- `NEO4J_USER`: Usuario de Neo4j (por defecto: `neo4j`)
- `NEO4J_PASSWORD`: Contraseña de Neo4j (ajusta según tu configuración)
- `DEFAULT_OUTPUT_FILENAME`: Nombre del archivo de salida por defecto
- `LIMIT_CHOKE_POINTS`: Límite de resultados para la consulta de priorización

### Uso

#### Uso Básico

Ejecuta el script sin argumentos para generar un informe con el nombre por defecto:

```bash
python ChokeHound.py
```

Esto generará un archivo `ChokeHound_report.xlsx` en el directorio actual.

#### Especificar Archivo de Salida

Para especificar un nombre de archivo personalizado:

```bash
python ChokeHound.py --output mi_informe.xlsx
```

O usando la forma corta:

```bash
python ChokeHound.py -o mi_informe.xlsx
```

#### Generar Log de Cálculos de Riesgo

Para generar un archivo de log detallado que explique cómo se calculó la puntuación de riesgo para cada punto de estrangulamiento:

```bash
python ChokeHound.py --output mi_informe.xlsx --log-risk
```

Esto generará dos archivos:
- `mi_informe.xlsx`: El informe Excel
- `mi_informe_risk_calculation_log.txt`: El log detallado de cálculos

### Estructura del Informe

El informe Excel generado contiene las siguientes hojas:

1. **Cover (Portada)**: Información general del informe, incluyendo fecha de generación, URI de Neo4j y descripción de cada hoja.

2. **1st degree (direct) relation to tier 0**: Relaciones directas donde el objetivo es Tier-0 y el origen NO es Tier-0. Muestra enlaces entre niveles que rompen el modelo de niveles.

3. **Direct relationships into Tier0**: Clasificación de tipos de relación que impactan directamente Tier-0 (Choke Points por tipo de borde).

4. **Source nodes into T0 Rank**: Top 100 nodos no Tier-0 con más conexiones directas a objetos Tier-0.

5. **Prioritise choke points**: Choke Points priorizados por puntuación de riesgo y número de rutas de ataque afectadas. Esta hoja incluye una columna `Risk` que calcula la puntuación de riesgo.

### Cálculo de Riesgo

La puntuación de riesgo se calcula usando la siguiente fórmula:

```
Riesgo = (PesoObjetoOrigen × CategoríaObjetoOrigen) +
         (PesoTipoRelación × CategoríaTipoRelación) +
         (PesoObjetoDestino × CategoríaObjetoDestino) +
         (PesoRutasAfectadas × MultiplicadorRutas × 10)
```

**Componentes**:

1. **Objeto Origen**: Tipo de objeto que tiene el privilegio (Usuario, Grupo, Computadora, etc.)
   - Grupos comunes por defecto (Everyone, Domain Users, etc.) tienen mayor riesgo
   - Peso por defecto: 0.25

2. **Tipo de Relación**: Tipo de privilegio otorgado (Owns, DCSync, AdminTo, etc.)
   - Privilegios más peligrosos tienen mayor categoría de riesgo
   - Peso por defecto: 0.35

3. **Objeto Destino**: Tipo de objeto Tier-0 objetivo (Domain, Computer, Group, etc.)
   - Objetos más críticos tienen mayor categoría de riesgo
   - Peso por defecto: 0.20

4. **Rutas de Ataque Afectadas**: Número de orígenes no Tier-0 que pueden alcanzar este punto de estrangulamiento
   - Multiplicador escalado según el número de rutas:
     - 0 rutas: 1.0x
     - 1-9 rutas: 1.2x
     - 10-49 rutas: 1.5x
     - 50-99 rutas: 2.0x
     - 100-499 rutas: 2.5x
     - 500+ rutas: 3.0x
   - Peso por defecto: 0.20

Los pesos y categorías pueden ajustarse editando el archivo `risk_config.py`.

### Ejemplos

#### Ejemplo 1: Análisis Básico

```bash
python ChokeHound.py
```

Genera `ChokeHound_report.xlsx` con todos los análisis.

#### Ejemplo 2: Análisis con Nombre Personalizado

```bash
python ChokeHound.py -o analisis_dominio_2024.xlsx
```

Genera un informe con nombre personalizado.

#### Ejemplo 3: Análisis Completo con Log de Riesgo

```bash
python ChokeHound.py --output analisis_completo.xlsx --log-risk
```

Genera el informe Excel y un archivo de log detallado con los cálculos de riesgo.

### Solución de Problemas

#### Error de Conexión a Neo4j

**Problema**: `❌ Error connecting to Neo4j: ...`

**Solución**:
1. Verifica que Neo4j esté ejecutándose
2. Verifica la URI, usuario y contraseña en `config.py`
3. Asegúrate de que el puerto 7687 (o el puerto configurado) esté accesible
4. Si usas Neo4j Desktop, verifica que la base de datos esté activa

#### Archivo Bloqueado

**Problema**: `❌ Error: The file '...' is currently open in another application.`

**Solución**: Cierra el archivo Excel si está abierto en otra aplicación y vuelve a ejecutar el script.

#### No se Encuentran Resultados

**Problema**: Las hojas muestran "No results found"

**Solución**:
1. Verifica que BloodHound haya importado datos en Neo4j
2. Verifica que los objetos estén etiquetados correctamente con `Tag_Tier_Zero`
3. Ejecuta las consultas de BloodHound para asegurar que hay datos disponibles

#### Error de Importación de Módulos

**Problema**: `ModuleNotFoundError: No module named 'py2neo'`

**Solución**: Instala las dependencias:
```bash
pip install py2neo pandas openpyxl
```

### Personalización

#### Ajustar Pesos de Riesgo

Edita `risk_config.py` para modificar los pesos en el cálculo de riesgo:

```python
RISK_WEIGHTS = {
    "source_object": 0.25,      # Peso para tipo de objeto origen
    "relationship_type": 0.35,  # Peso para tipo de relación
    "target_object": 0.20,      # Peso para tipo de objeto destino
    "affected_attack_paths": 0.20  # Peso para rutas de ataque afectadas
}
```

#### Modificar Categorías de Riesgo

Puedes ajustar las categorías de riesgo para diferentes tipos de objetos y relaciones editando los diccionarios en `risk_config.py`:
- `SOURCE_OBJECT_CATEGORIES`
- `RELATIONSHIP_TYPE_CATEGORIES`
- `TARGET_OBJECT_CATEGORIES`

#### Cambiar Límite de Resultados

Modifica `LIMIT_CHOKE_POINTS` en `config.py` para cambiar el número máximo de Choke Points en la hoja de priorización.

### Estructura del Proyecto

```
Script/
├── ChokeHound.py          # Script principal
├── config.py              # Configuración de conexión a Neo4j
├── queries.py             # Consultas Cypher para análisis
├── risk_config.py         # Configuración de cálculo de riesgo
└── README.md              # Este archivo
```

### Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz un fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/nueva-caracteristica`)
3. Realiza commit de tus cambios (`git commit -am 'Añade nueva característica'`)
4. Haz push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

### Licencia

[Especificar licencia aquí]

### Autor

[Tu nombre/usuario de GitHub]

---

## ChokeHound - BloodHound Choke Points Analyzer

ChokeHound is a security analysis tool that identifies critical choke points in Active Directory using data collected by BloodHound. Choke points are critical privilege relationships that connect non-Tier-0 objects to Tier-0 objects, representing optimal locations to block the largest number of attack paths.

### Features

- **Choke Point Identification**: Finds direct relationships between non-Tier-0 and Tier-0 objects
- **Risk-Based Prioritization**: Calculates a risk score for each choke point based on multiple factors
- **Attack Path Analysis**: Identifies how many attack paths are affected by each choke point
- **Excel Reports**: Generates detailed reports in Excel format with multiple worksheets
- **Risk Calculation Log**: Option to generate a detailed log file explaining risk calculations

### Prerequisites

- Python 3.7 or higher
- Neo4j (version 4.x or higher recommended)
- BloodHound with data imported into Neo4j
- Access to BloodHound's Neo4j database

### Requirements Before Execution

1. **BloodHound CE installation**: Deploy BloodHound Community Edition and ensure the Neo4j backend is initialized and reachable with valid credentials.
2. **Data collection with SharpHound or AzureHound**: Run the official collectors (SharpHound for on-prem AD or AzureHound for Azure AD) and ingest the results into BloodHound CE so the database is populated.
3. **Tier 0 configuration inside BloodHound**: Tag every Tier-0 asset with `Tag_Tier_Zero` (domains, groups, privileged accounts, DCs). ChokeHound relies on this tagging to surface the correct choke points.

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/ChokeHound.git
   cd ChokeHound/Script
   ```

2. **Install Python dependencies**:
   ```bash
   pip install py2neo pandas openpyxl
   ```
   
   Or create a `requirements.txt` file with the following content:
   ```
   py2neo>=2021.2.3
   pandas>=1.3.0
   openpyxl>=3.0.9
   ```
   
   Then install:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Neo4j is running**:
   Make sure your Neo4j instance with BloodHound data is running and accessible.

### Configuration

Edit the `config.py` file to configure the Neo4j connection:

```python
# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "bloodhoundcommunityedition"

# Default output filename
DEFAULT_OUTPUT_FILENAME = "ChokeHound_report.xlsx"

# Limit for "Prioritise choke points" query
LIMIT_CHOKE_POINTS = 200
```

**Configuration parameters**:
- `NEO4J_URI`: Neo4j connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USER`: Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD`: Neo4j password (adjust according to your configuration)
- `DEFAULT_OUTPUT_FILENAME`: Default output filename
- `LIMIT_CHOKE_POINTS`: Result limit for the prioritization query

### Usage

#### Basic Usage

Run the script without arguments to generate a report with the default name:

```bash
python ChokeHound.py
```

This will generate a `ChokeHound_report.xlsx` file in the current directory.

#### Specify Output File

To specify a custom filename:

```bash
python ChokeHound.py --output my_report.xlsx
```

Or using the short form:

```bash
python ChokeHound.py -o my_report.xlsx
```

#### Generate Risk Calculation Log

To generate a detailed log file explaining how the risk score was calculated for each choke point:

```bash
python ChokeHound.py --output my_report.xlsx --log-risk
```

This will generate two files:
- `my_report.xlsx`: The Excel report
- `my_report_risk_calculation_log.txt`: The detailed calculation log

### Report Structure

The generated Excel report contains the following sheets:

1. **Cover**: General report information, including generation date, Neo4j URI, and description of each sheet.

2. **1st degree (direct) relation to tier 0**: Direct relationships where the target is Tier-0 and the source is NOT Tier-0. Shows cross-tier links that break the tiering model.

3. **Direct relationships into Tier0**: Ranking of relationship types that directly hit Tier-0 (edge-type choke points).

4. **Source nodes into T0 Rank**: Top 100 non-Tier-0 nodes with the most direct connections to Tier-0 objects.

5. **Prioritise choke points**: Prioritized choke points ranked by risk score and number of affected attack paths. This sheet includes a `Risk` column that calculates the risk score.

### Risk Calculation

The risk score is calculated using the following formula:

```
Risk = (SourceObjectWeight × SourceObjectCategory) +
       (RelationshipTypeWeight × RelationshipTypeCategory) +
       (TargetObjectWeight × TargetObjectCategory) +
       (AffectedAttackPathsWeight × PathsMultiplier × 10)
```

**Components**:

1. **Source Object**: Type of object that has the privilege (User, Group, Computer, etc.)
   - Common default groups (Everyone, Domain Users, etc.) have higher risk
   - Default weight: 0.25

2. **Relationship Type**: Type of privilege granted (Owns, DCSync, AdminTo, etc.)
   - More dangerous privileges have higher risk categories
   - Default weight: 0.35

3. **Target Object**: Type of Tier-0 target object (Domain, Computer, Group, etc.)
   - More critical objects have higher risk categories
   - Default weight: 0.20

4. **Affected Attack Paths**: Number of non-Tier-0 origins that can reach this choke point
   - Multiplier scaled according to number of paths:
     - 0 paths: 1.0x
     - 1-9 paths: 1.2x
     - 10-49 paths: 1.5x
     - 50-99 paths: 2.0x
     - 100-499 paths: 2.5x
     - 500+ paths: 3.0x
   - Default weight: 0.20

Weights and categories can be adjusted by editing the `risk_config.py` file.

### Examples

#### Example 1: Basic Analysis

```bash
python ChokeHound.py
```

Generates `ChokeHound_report.xlsx` with all analyses.

#### Example 2: Analysis with Custom Name

```bash
python ChokeHound.py -o domain_analysis_2024.xlsx
```

Generates a report with a custom name.

#### Example 3: Complete Analysis with Risk Log

```bash
python ChokeHound.py --output complete_analysis.xlsx --log-risk
```

Generates the Excel report and a detailed log file with risk calculations.

### Troubleshooting

#### Neo4j Connection Error

**Problem**: `❌ Error connecting to Neo4j: ...`

**Solution**:
1. Verify that Neo4j is running
2. Check the URI, username, and password in `config.py`
3. Ensure port 7687 (or your configured port) is accessible
4. If using Neo4j Desktop, verify that the database is active

#### File Locked

**Problem**: `❌ Error: The file '...' is currently open in another application.`

**Solution**: Close the Excel file if it's open in another application and run the script again.

#### No Results Found

**Problem**: Sheets show "No results found"

**Solution**:
1. Verify that BloodHound has imported data into Neo4j
2. Verify that objects are correctly labeled with `Tag_Tier_Zero`
3. Run BloodHound queries to ensure data is available

#### Module Import Error

**Problem**: `ModuleNotFoundError: No module named 'py2neo'`

**Solution**: Install dependencies:
```bash
pip install py2neo pandas openpyxl
```

### Customization

#### Adjust Risk Weights

Edit `risk_config.py` to modify weights in the risk calculation:

```python
RISK_WEIGHTS = {
    "source_object": 0.25,      # Weight for source object type
    "relationship_type": 0.35,  # Weight for relationship type
    "target_object": 0.20,      # Weight for target object type
    "affected_attack_paths": 0.20  # Weight for affected attack paths
}
```

#### Modify Risk Categories

You can adjust risk categories for different object and relationship types by editing the dictionaries in `risk_config.py`:
- `SOURCE_OBJECT_CATEGORIES`
- `RELATIONSHIP_TYPE_CATEGORIES`
- `TARGET_OBJECT_CATEGORIES`

#### Change Result Limit

Modify `LIMIT_CHOKE_POINTS` in `config.py` to change the maximum number of choke points in the prioritization sheet.

### Project Structure

```
Script/
├── ChokeHound.py          # Main script
├── config.py              # Neo4j connection configuration
├── queries.py             # Cypher queries for analysis
├── risk_config.py         # Risk calculation configuration
└── README.md              # This file
```

### Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

### License

[Specify license here]

### Author

[Your name/GitHub username]

