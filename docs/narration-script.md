# CreditAgent walkthrough: narration script

Read this over `creditagent-walkthrough.mp4` if you want a voiceover. Timings match the video (about 2 minutes). Roughly 280 words, so speak at a relaxed pace.

| Time | Scene | Say |
|---|---|---|
| 0:00 | Title | This is CreditAgent, a LangGraph agent that underwrites a retail loan file and writes the credit memo. |
| 0:04 | The problem | Most underwriting time goes on reconciliation. Does the payslip match the bank credits? Does the bureau show every loan? Each document can look fine on its own. The risk sits in the gaps between them. |
| 0:13 | The graph | The agent is eight nodes sharing one typed state. Each node is a plain Python function that returns only the keys it changes, so every step is testable on its own. |
| 0:21 | Step 1, ingest | Ingest loads the file and checks the right income proof is there. If anything is missing, a conditional edge ends the graph early. |
| 0:29 | Step 2, extract | Extract turns the payslip, bank statement and bureau report into structured fields. |
| 0:37 | Step 3, discrepancies | This is the step most tools skip. For Rahul, the salary is paid by a different employer, at ninety-two thousand, not one and a half lakh. And there's an eighteen-thousand EMI that the bureau doesn't show. |
| 0:48 | Step 4, analyze | So the agent underwrites on the lowest verified income. FOIR is 59.6 percent, not the 24.5 the declared numbers suggest. |
| 0:58 | Step 5, policy | Eight policy rules. Hard rules can decline a file; soft rules send it for review. |
| 1:07 | Step 6, risk grade | The grade is a transparent points model, so every deduction can be explained to a credit committee. |
| 1:14 | Step 7, decide | When documents disagree, the data can't be trusted yet, so the file goes to a human first. Rahul's file is referred. |
| 1:23 | Step 8, memo | Finally it writes the credit memo: facility, analysis, policy table, red flags and reasons. |
| 1:30 | Outcomes | Three synthetic files, three different decisions from the same pipeline: approve, refer and decline. |
| 1:40 | Guardrail | If an LLM writes the commentary, every number it uses is checked against the source data. One invented figure and the draft is discarded. |
| 1:49 | Evals | An eval harness checks decisions, red-flag precision and recall, and memo grounding on every push. |
| 1:57 | Outro | It runs offline with no API key. The code is on my GitHub. |

To add your voice: record the script on your phone, then combine the two in any video editor (CapCut, iMovie, Clipchamp), or with ffmpeg:

```bash
ffmpeg -i creditagent-walkthrough.mp4 -i voice.m4a -c:v copy -c:a aac -shortest walkthrough-voiced.mp4
```
