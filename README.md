# AI Complaint Resolution Agent 🛡️

An AI-powered customer support application built with **CrewAI**, **Groq (`openai/gpt-oss-120b`)**, and **Streamlit**.

## Features
- **Deterministic Tool Verification:** Integrates policy JSON lookup and order CSV queries.
- **5-Step Workflow:** Analyzes urgency, looks up data, decides action, drafts replies, and issues tickets.
- **Strict Validation:** Structured Pydantic outputs prevent model output formatting errors.
- **Downloadable Tickets:** Export JSON ticket records directly from the interface.

## Quickstart

```cmd
git clone [https://github.com/YOUR_USERNAME/ai-complaint-resolution-agent.git](https://github.com/YOUR_USERNAME/ai-complaint-resolution-agent.git)
cd ai-complaint-resolution-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
