# ST-LMS v3: Core Architecture & Philosophy

## 1. Filosofi Inti ( STRICT GUARDRAILS )
- ST-LMS v3 BUKAN bot trading monolitik. Ini adalah "Trading Operating System" berbasis Truth-First Architecture.
- "Truth Layer" (Supertrend Point, Line, Wave) adalah SATU-SATUNYA sumber kebenaran (Single Source of Truth).
- DILARANG KERAS menggunakan Vector Database (Chroma, Pinecone, dll) atau LLM untuk analisis market. Gunakan "Structural RAG" (JSON + Index + Binary Search).
- DILARANG KERAS menggunakan SQLite/PostgreSQL untuk pipeline live/real-time. Database hanya untuk Archive/Audit. Pipeline live wajib menggunakan JSON Data Lake + Memory Index.
- Semua waktu WAJIB menggunakan WIB dan memiliki "Time ID" (contoh: `P2607081920`) untuk memudahkan audit.
- Worker TIDAK BOLEH trading langsung. Worker hanya mengeluarkan "Proposal". HiveMind yang mengumpulkan, Portfolio Manager yang mengekusi.

## 2. Pipeline Utama
Scanner (Download) -> Normalizer (WIB & Time ID) -> Observe (Raw Facts) -> Truth Layer (Point/Line/Wave) -> Validation (Semantic) -> Structural RAG -> Workers (Proposal) -> HiveMind -> Portfolio -> Execution -> Exit.

## 3. Aturan Eksekusi Kode
- TUNGGU PERINTAH: Jangan menulis seluruh sistem sekaligus. Kita bangun modul per modul (Sprint).
- TIAP FILE WAJIB MEMILIKI: Docstring, Type Hinting (Python typing), dan Error handling yang mencatat ke "Audit Log".
- DILARANG OVER-ENGINEERING: Gunakan `dataclass` atau `Pydantic` untuk schema JSON. Jangan membuat kelas abstrak yang rumit jika tidak diminta.
