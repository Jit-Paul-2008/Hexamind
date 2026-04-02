# Next Session Plan

## Session Handoff Snapshot

- Backend and frontend are integrated with live SSE pipeline flow.
- Structured long-form synthesis is active in A4-like output mode.
- Internet retrieval is integrated and source inventory appears in final report.
- Draggable agent and processing windows are available with overlap handling.
- Build and test status was green at handoff time.

## Tomorrow Start Checklist

1. Run local stack and verify health payload includes webResearchEnabled true.
2. Run one live query and confirm source inventory contains real urls.
3. Validate that evidence snapshot lines contain substantive findings.
4. Prioritize export track implementation in this order: docx, pptx, audio.

## Planned Implementation Track

### Track A: Quality and Grounding

1. Add citation-to-claim linking in synthesis section bodies.
2. Add source credibility scoring and confidence calibration.
3. Add regeneration gate when citation count is below threshold.

### Track B: Downloadable Outputs

1. DOCX export service
- Input: synthesis markdown + metadata
- Output: .docx file
- Include sections, numbered headings, bullets, source inventory table

2. PPTX export service
- Input: synthesis markdown + metadata
- Output: .pptx file
- Slide layout:
  - Title slide
  - Executive summary
  - Key findings
  - Comparative analysis
  - Recommendation and action plan
  - Sources and confidence

3. Audio export service
- Input: synthesized report text + voice settings
- Output: .mp3 or .wav
- Include optional short intro and section pauses

### Track C: Frontend UX

1. Add export toolbar in output window: Download DOCX, Download PPTX, Download Audio.
2. Add export progress and error states.
3. Add file size and generation time hints.

## Suggested API Endpoints

- POST /api/export/docx
- POST /api/export/pptx
- POST /api/export/audio
- GET /api/export/{jobId}/status
- GET /api/export/{jobId}/download

## Risks to Address

- Long export runtime for large reports.
- Audio generation cost and latency.
- Citation drift when regenerating final synthesis.
- Security checks for remote source content before export.
