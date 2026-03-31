# AI Study Agent

**Turn a learning goal into a structured plan—with explanations, leveled questions, and instant feedback—in one focused workspace.**

---

## Overview

AI Study Agent is a Streamlit application that uses the OpenAI API to help you study with purpose. Describe what you want to learn, optionally attach reference material, and get an organized plan: topics broken down, explanations at the right level, and practice questions from easy to hard. An interactive flow lets you answer in the app, check your work against model feedback, and review mistakes and tips—useful whether you are preparing for an exam or building a new skill.

---

## Features

- **Structured study plans** — Clear milestones and pacing aligned to your goal and time available  
- **Topic breakdown** — Subtopics and hierarchy so you know what to tackle next  
- **Explanations** — Content tuned to beginner, intermediate, or advanced  
- **Question sets** — Easy, medium, and hard items tied to the plan  
- **Interactive answering** — Submit answers, check them, and see verdicts with explanations and reference solutions  
- **Modern UI** — Tabbed workspace, light/dark themes, Material Icons, and local plan history  

Optional **PDF** context and **SQLite** storage under `data/` keep plans grounded and persistent on your machine.

---

## Demo flow

1. Enter your study goal, level, and time; optionally upload a PDF.  
2. **Generate study plan** and browse **Plan**, **Topics**, **Learn**, and related tabs.  
3. In **Questions**, write answers and use **Check answers**.  
4. Open **Feedback** for detailed results; review **Mistakes** and **Tips** when present.  
5. Use the sidebar to reopen saved plans and track checkpoints.

---

## Tech stack

| | |
|:---|:---|
| **Language** | Python |
| **Model** | OpenAI API |
| **Interface** | Streamlit |

Supporting libraries include **pypdf** (PDF text extraction) and **SQLite** (local persistence). Model and paths are configurable via `config.py`.

---

## How to run

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Set your API key** (do not commit real keys)

```bash
export OPENAI_API_KEY="your_key"
```

**3. Start the app**

```bash
streamlit run app.py
```

The app opens in your browser. Ensure `OPENAI_API_KEY` is set in the same environment you use to run Streamlit.

---

*Built for learners who want structure, not noise—verify critical facts against your course materials when it matters.*
