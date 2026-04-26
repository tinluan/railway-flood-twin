# 📚 How to Use Scientific References with VS Code Copilot

GitHub Copilot cannot read PDF files directly. To solve this, we convert our key papers into Markdown format that Copilot can read and understand.

---

## Where are the Markdown References?
**Location on Shared Drive:**
`G:\Shared drives\DigiTwin\railway-flood-twin\data\references\markdown\`

**Access via code:**
```python
from src.utils.paths import paths
markdown_folder = paths.REFERENCES_MD  # Points to the markdown/ subfolder
```

---

## How to use them with GitHub Copilot

### Step 1: Open the relevant Markdown file in VS Code
In your VS Code file explorer, navigate to:
`G:\Shared drives\DigiTwin\railway-flood-twin\data\references\markdown\`

Open the paper you need, for example:
`RISK VIP Evaluation of Flood Risk on the French Railway Network Using an Innovative GIS Approach.md`

### Step 2: Ask Copilot about the paper
With the Markdown file open in a tab, open Copilot Chat (`Ctrl+Alt+I`) and ask:
> *"Based on the RISK VIP paper I have open, what flood risk thresholds do they use for railway embankments?"*

Or for writing code:
> *"Using the methodology in the open paper, help me write a Python function that applies the rainfall threshold logic to our GIS polygons."*

### Step 3: Cross-reference with our project
For the best results, open both the Markdown paper **AND** `src/utils/paths.py` in your tabs. Then ask Copilot:
> *"Using the methods from the RISK VIP paper and our paths.py, write a script that computes flood risk scores for each gis_asset."*

---

## Available Converted Papers (Key References)
| Filename | Topic | Best for |
| :--- | :--- | :--- |
| `RISK VIP Evaluation of Flood Risk...md` | Railway flood risk (GIS) | Risk Engine, Methodology |
| `Development of fragility curves...md` | Scour risk on embankments | Risk thresholds, formulas |
| `Integrated representation of geospatial data...md` | Digital Twin GIS integration | Architecture, BIM/GIS |
| `Digital twin in railway industry...md` | DT literature review | Introduction, Background |

---

## Adding More Conversions
If you need another paper converted from PDF to Markdown, use this script:
```powershell
$env:PYTHONPATH = "."; .\.conda\python.exe src/utils/pdf_to_markdown.py `
  "G:\Shared drives\DigiTwin\railway-flood-twin\data\references\PAPER_NAME.pdf" `
  "G:\Shared drives\DigiTwin\railway-flood-twin\data\references\markdown\PAPER_NAME.md"
```
Or just ask Tin to have Antigravity convert it for the whole team.
