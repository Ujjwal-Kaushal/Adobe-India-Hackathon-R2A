# Adobe India Hackathon - Round 1A Submission

## Challenge Theme: Connecting the Dots Through Docs  
**Mission**: Extract a structured outline from a given PDF file (up to 50 pages), consisting of the **Title** and **Headings (H1, H2, H3)** in a clean hierarchical JSON format.

---

## 🧠 Approach

Our solution implements a **robust, multilingual-friendly PDF outline extractor** that avoids hardcoded rules and instead uses layout, font properties, and structural patterns.

Key steps in the approach:

1. **Preprocessing**:
   - Load each PDF from the `/app/input` directory.
   - Analyze font sizes across the document to determine the **body text baseline**.
   - Detect and exclude repetitive **footer elements**.

2. **Title Extraction**:
   - Titles are detected from the top half of the first page using:
     - Font size threshold
     - Centering and bold heuristics
     - Line merging and cleanup

3. **Heading Detection**:
   - Apply multiple heuristics including:
     - Font size and boldness
     - Text alignment
     - Regex-based detection of numbered headings (e.g., `1.1`, `Chapter 2`, `Appendix A`)
     - Uppercase and font weight cues
   - Avoid false positives using:
     - Sentence-like ending filters
     - Date and footer filtering

4. **Heading Level Assignment**:
   - Use font size tiers and numbering pattern depth to assign `H1`, `H2`, `H3`, etc.
   - Post-process to ensure logical hierarchy (e.g., no H3 immediately after H1)

5. **Output Format**:
   - Export final results to `/app/output` as per expected format:
     ```json
     {
       "title": "Document Title",
       "outline": [
         { "level": "H1", "text": "Section Heading", "page": 1 },
         ...
       ]
     }
     ```

---

## 🧰 Models / Libraries Used

- **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/en/latest/)**: For efficient, fast PDF parsing and extraction of layout and text features
- **Python Standard Libraries**: `re`, `statistics`, `pathlib`, `json`, `collections`, `logging`

> 🚫 No heavy ML/DL models are used. The solution is fully rule-based with compact logic to meet performance and size constraints.

---

## 🐳 How to Build and Run

This project is fully containerized and offline-compatible.

### 🏗️ Build Docker Image
```bash
docker build --platform linux/amd64 -t pdf-outliner:round1a .
```

### 🚀 Run the Container
```bash
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outliner:round1a
```

This will automatically process all PDF files in the input/ directory and write the corresponding .json outline files to the output/ directory.

---

## ✅ Key Features

⚡ Fast processing (≤ 10s for a 50-page document)

🌐 Multilingual-safe (language-agnostic heading detection)

🧠 Accurate structural detection (via font + layout + numbering heuristics)

🔒 Fully offline (no external API or internet calls)

🐳 Dockerized and fully AMD64-compatible

---

## 📁 Project Structure

```bash
.
├── extract_outline.py     # Main script with PDFOutlineExtractor class
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
├── input/                 # Directory for input PDFs (volume mounted)
└── output/                # Directory for output JSONs (volume mounted)
```

---

## ✍️ Authors

Developed by Team **SUV** for Adobe India Hackathon 2025 – Round 1A.

- Saharsh Jain
- Ujjwal Kaushal
- Vinit Vinayak Pandey