# 15-Minute Operational Re-computation Diagram

This document contains the Mermaid diagram illustrating the automated 15-minute operational cycle. The loop orchestrates the ingestion of live rainfall data, HEC-RAS hydraulic re-computation, asset risk assessment, and system alert updates.

---

## Process Flow Diagram

```mermaid
flowchart TD
    %% Styling Definitions
    classDef trigger fill:#e1bee7,stroke:#8e24aa,stroke-width:2px,color:#000;
    classDef layer1 fill:#bbdefb,stroke:#1976d2,stroke-width:2px,color:#000;
    classDef layer2 fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef decision fill:#ffecb3,stroke:#ffa000,stroke-width:2px,color:#000;
    classDef layer3 fill:#ffcc80,stroke:#f57c00,stroke-width:2px,color:#000;
    classDef layer4 fill:#ffcdd2,stroke:#d32f2f,stroke-width:2px,color:#000;
    classDef output fill:#cfd8dc,stroke:#455a64,stroke-width:2px,color:#000;

    %% Nodes
    Start(["⏱️ 15-Minute Trigger (or Manual Click)"])
    
    subgraph L1 ["Layer 1: Meteorology"]
        API["☁️ Open-Meteo API<br/>(Fetch 48h Forecast)"]
        CSV["📄 Update CSV<br/>(rainfall_live.csv)"]
    end

    subgraph L2 ["Layer 2: Hydrology"]
        SWI["💧 SWI Calculator<br/>(Recursive Leaky Bucket)"]
        Runoff["🌊 Runoff Coefficient<br/>(Sigmoid Curve)"]
    end

    Eval{"Is Peak SWI ><br/>100mm Threshold?"}

    subgraph L3 ["Layer 3: Hydraulics"]
        Inject["✏️ Inject Precipitation<br/>(CAPSTONE_JN_L752_PK.u01)"]
        HEC["⚙️ HEC-RAS 2D<br/>(COM API Simulation)"]
        HDF["📊 Extract WSE<br/>(HDF5 Reader)"]
    end

    subgraph L4 ["Layer 4: Vulnerability & RAMS"]
        Fragility["📉 Fragility Curves<br/>(P_failure Calculation)"]
        Alerts["🚦 Generate Alerts<br/>(Green / Yellow / Red)"]
    end

    Dashboard(["🖥️ Update Dashboard UI & Logs"])
    NoRun(["⏭️ Use Existing WSE Results"])

    %% Connections
    Start --> API
    API --> CSV
    CSV --> SWI
    SWI --> Runoff
    Runoff --> Eval

    Eval -->|"Yes (High Flood Risk)"| Inject
    Inject --> HEC
    HEC --> HDF
    HDF --> Fragility

    Eval -->|"No (Low Risk)"| NoRun
    NoRun --> Fragility

    Fragility --> Alerts
    Alerts --> Dashboard

    %% Apply Classes
    class Start trigger;
    class API,CSV layer1;
    class SWI,Runoff layer2;
    class Eval decision;
    class Inject,HEC,HDF layer3;
    class Fragility,Alerts layer4;
    class Dashboard,NoRun output;
```

---

## Detailed Step-by-Step Instructions

### 1. Ingestion Stage (Minutes 0 - 2)
* **Trigger:** A background task runner (such as Windows Task Scheduler or a Python schedule loop) triggers every 15 minutes.
* **Open-Meteo API:** A Python script requests current and forecast rainfall rates using geographical coordinates for the railway corridor.
* **Database Write:** The fetched rainfall values are logged to the database with a timestamp.

### 2. Boundary Condition Prep (Minutes 2 - 3)
* **Flow File Generator:** The pipeline reads the latest rainfall volume and maps it into an unsteady flow input file (`.u01` or similar hydrograph format) accepted by the HEC-RAS model.

### 3. HEC-RAS Execution (Minutes 3 - 10)
* **COM API Control:** The pipeline starts HEC-RAS in background mode via Python's `win32com` library (`hecras_bridge.py`).
* **Compute Loop:** The HEC-RAS hydraulic engine runs the unsteady flow simulation, calculating water surface elevation (WSE) values along the cross sections.

### 4. Post-processing & Extraction (Minutes 10 - 12)
* **HDF5 Parsing:** HEC-RAS writes its outputs to a binary `.hdf` file. The pipeline parses this file using `h5py` to read the calculated profile WSE values at specific cross sections.
* **WSE Storage:** The extracted elevations are saved back into the database.

### 5. Risk Assessment & Alerts (Minutes 12 - 15)
* **Asset Assessment:** The engine calculates clearance metrics by subtracting local WSE values from the physical datum levels of tracks, tunnels, and bridge decks.
* **Alert Triggering:** If clearance falls below safety thresholds, risk levels are marked (e.g., Red/Critical, Yellow/Warning).
* **UI Update:** The Streamlit dashboard live-polls the database, visualising the revised risk ratings and warning banners instantly.

---

## HEC-RAS COM API Integration Detail

This sequence diagram illustrates exactly how the Python bridge interacts with HEC-RAS using the Windows Component Object Model (COM) interface to bypass runtime limitations and extract results.

```mermaid
sequenceDiagram
    autonumber
    participant App as "Python Bridge (win32com)"
    participant FS as "File System (.u01)"
    participant HEC as "HEC-RAS 6.7 (COM API)"
    participant Out as "File System (.hdf)"

    App->>HEC: Connect to ProgID ("RAS67.HECRASController")
    App->>HEC: Project_Open("FloodTwin.prj")
    Note over App,FS: COM API lacks precipitation editing,<br/>so we directly edit the plain-text file.
    App->>FS: Read live rainfall CSV data
    App->>FS: Parse Unsteady Flow File (.u01)
    App->>FS: Overwrite "Precipitation Hydrograph=" block
    App->>HEC: Compute_CurrentPlan(wait=True)
    activate HEC
    Note over HEC: Hydraulic Engine Computes WSE
    HEC-->>Out: Write Results to Binary (.hdf)
    HEC-->>App: Return Compute Status (Success/Fail)
    deactivate HEC
    App->>HEC: Output_NodeOutput(...) [1D WSE Extraction]
    App->>Out: h5py read WSE [2D Area Extraction]
    App->>HEC: Project_Close() & QuitRas()
```

---

## How to View and Export the Diagram to PDF

Markdown files do not natively render interactive diagrams, but you can view and export this Mermaid flowchart using any of the following methods:

### Method A: VS Code Extensions (Recommended)
1. **View Live:**
   * Open this file (`diagram.md`) in VS Code.
   * Search for and install the extension **Markdown Preview Mermaid Support** (by Matt Bierner).
   * Press `Ctrl + Shift + V` (Windows) to open the Markdown preview pane. The diagram will render dynamically.
2. **Export to PDF:**
   * Install the **Markdown PDF** extension (by yzane) in VS Code.
   * Open `diagram.md` in your editor, right-click, and select **Markdown PDF: Export (pdf)**.
   * *Note: Ensure your Markdown PDF settings have Mermaid support enabled, or use a markdown editor like Typora/Obsidian.*

### Method B: Mermaid Live Editor (Web-based & Cleanest Export)
1. Copy the code block starting with ````mermaid` and ending with ```` from this file.
2. Go to [Mermaid Live Editor](https://mermaid.live).
3. Paste the code into the **Code** section on the left.
4. The diagram will instantly render on the right.
5. Click **Actions** at the bottom of the left/preview pane:
   * Select **Download PNG** or **Download SVG** for high-resolution images.
   * Select **Print / PDF** to save or print the diagram directly to a PDF page.

### Method C: Obsidian or Typora (Desktop Apps)
1. Open this project directory in **Obsidian** or open the file in **Typora**.
2. Both editors support Mermaid natively.
3. Use the app's native export menu: `File` -> `Export` -> `PDF`.
