"""
Dataset Builder for Gemini Flow 600-Run Speech Benchmark Suite.
Generates 100 distinct 16kHz mono audio samples covering:
- 8 Speech Types: Technical jargon, rapid casual conversation, whisper/quiet speech,
  conference meetings, legal/medical terminology, code dictation, storytelling, multilingual accents.
- 6 Acoustic Environments: Clean studio, low SNR, street noise, AC hum, reverb/echo, compressed mic.
- 4 Durations: Micro-bursts (1-3s), short phrases (5-10s), medium dictation (15-30s), extended continuous speech (45-60s).
- 100 Deterministic Formatting & Transformation Task Specifications.
"""
import os
import sys
import json
import time
import wave
import tempfile
from pathlib import Path
import numpy as np
import scipy.signal
import soundfile as sf
import win32com.client

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_samples"
GT_DIR = BASE_DIR / "ground_truth"
MANIFEST_PATH = BASE_DIR / "manifest.json"
FORMATS_PATH = BASE_DIR / "formats_manifest.json"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
GT_DIR.mkdir(parents=True, exist_ok=True)

# 100 Distinct Audio Corpus Definitions
# Tuple format: (speech_type, acoustic_env, duration_class, text)
CORPUS = [
    # 1-15: Technical Jargon
    ("technical_jargon", "clean_studio", "short", "The Kubernetes cluster auto-scaled three additional worker pods across the secondary availability zone."),
    ("technical_jargon", "ac_hum", "short", "We optimized the PyTorch tensor operations with CUDA kernels to eliminate redundant memory transfers."),
    ("technical_jargon", "clean_studio", "medium", "Our distributed microservices architecture communicates via asynchronous gRPC streams backed by an Apache Kafka message bus with idempotent producers."),
    ("technical_jargon", "low_snr", "short", "The PostgreSQL query planner failed to use the partial index due to missing statistics on the JSONB column."),
    ("technical_jargon", "street_noise", "medium", "We implemented Redis caching with a write-through strategy to guarantee cache consistency across multiple regional deployment zones."),
    ("technical_jargon", "reverb", "short", "The OAuth2 authorization server issued a signed JWT containing custom role claims with an expiry of thirty minutes."),
    ("technical_jargon", "compressed_mic", "medium", "Terraform provisioned the AWS VPC peering connection and automatically updated the route tables and security groups."),
    ("technical_jargon", "clean_studio", "micro", "Deploy the container image to production."),
    ("technical_jargon", "low_snr", "medium", "The GraphQL federation gateway resolves subgraphs concurrently while enforcing schema directive validation at runtime."),
    ("technical_jargon", "ac_hum", "long", "The Elasticsearch cluster experienced high JVM garbage collection pressure during the hourly log re-indexing cycle. We tuned the heap allocation to thirty-two gigabytes, disabled swap memory entirely, and adjusted the shard count to prevent segment thrashing."),
    ("technical_jargon", "clean_studio", "short", "We configured Prometheus to scrape telemetry metrics from our FastAPI application at fifteen-second intervals."),
    ("technical_jargon", "compressed_mic", "micro", "Kill the stalled daemon process."),
    ("technical_jargon", "street_noise", "short", "The WebAssembly module executes cryptographic hashing directly in the browser with near-native CPU efficiency."),
    ("technical_jargon", "reverb", "medium", "Nginx acts as a reverse proxy terminating SSL connections and routing API traffic to the upstream uWSGI application pool."),
    ("technical_jargon", "clean_studio", "long", "By migrating our columnar data warehouse from Snowflake to Google BigQuery, our data engineering pipeline achieved a forty percent latency reduction in real-time aggregation queries, while partition pruning eliminated ninety gigabytes of unneeded scanned bytes per hour."),

    # 16-30: Rapid Casual Conversation
    ("rapid_casual", "clean_studio", "micro", "Hey Sarah, grab coffee?"),
    ("rapid_casual", "street_noise", "short", "Yeah honestly I think we should just push the sync to tomorrow morning after standup."),
    ("rapid_casual", "clean_studio", "short", "Did you see that pull request Alex opened? The diff is like three thousand lines."),
    ("rapid_casual", "low_snr", "medium", "I was talking to Dave earlier and he said the client wants the mockup done before lunch, but honestly that seems completely unrealistic given our current sprint backlog."),
    ("rapid_casual", "compressed_mic", "short", "Let me double check my calendar real quick, I might have a conflict at two thirty."),
    ("rapid_casual", "ac_hum", "medium", "So basically what happened was the build broke right when everyone was heading out, and we had to revert the merge commit to get staging back online."),
    ("rapid_casual", "clean_studio", "micro", "Sounds good, see you there!"),
    ("rapid_casual", "reverb", "short", "Wait, did anyone actually test the Stripe webhook on the sandbox environment yet?"),
    ("rapid_casual", "street_noise", "medium", "I'm literally on my way to the office right now, train got delayed like ten minutes, but I'll hop on the Slack huddle as soon as I sit down."),
    ("rapid_casual", "clean_studio", "long", "Look, I know everyone is stressed about the Q3 launch date, but if we rush the payment gateway refactor without full unit test coverage, we are going to end up fighting fires all weekend. I'd rather tell the product manager we need three more days and ship something bulletproof."),
    ("rapid_casual", "low_snr", "short", "Can you ping me the Figma link when you get a chance?"),
    ("rapid_casual", "clean_studio", "micro", "Thanks a million!"),
    ("rapid_casual", "compressed_mic", "medium", "Honestly the new dark mode theme looks so much cleaner than the old gray one. The contrast ratio on the buttons makes it way easier to read."),
    ("rapid_casual", "ac_hum", "short", "Let's just wrap up early today and pick this up first thing Monday."),
    ("rapid_casual", "clean_studio", "long", "We ordered pizza for the team hackathon tonight, so if you're planning on staying late to finish the demo widgets, head over to the main kitchen around seven. We got vegetarian, gluten-free, and regular pepperoni options for everyone."),

    # 31-40: Whisper / Quiet Speech
    ("whisper_quiet", "clean_studio", "micro", "Please keep your voice down."),
    ("whisper_quiet", "clean_studio", "short", "I think the client is waiting in the executive conference room right now."),
    ("whisper_quiet", "low_snr", "short", "Don't share the salary spreadsheet until management gives the official approval."),
    ("whisper_quiet", "clean_studio", "medium", "The confidential merger documents are locked in the legal directory. Only the senior partners have read access to the encrypted drive."),
    ("whisper_quiet", "ac_hum", "short", "The patient is resting now, so let us review the surgical charts outside."),
    ("whisper_quiet", "clean_studio", "micro", "Check the server log quietly."),
    ("whisper_quiet", "reverb", "medium", "We need to discuss the restructuring plan privately before the company-wide all-hands meeting at three o'clock."),
    ("whisper_quiet", "compressed_mic", "short", "Make sure your microphone is muted during the keynote presentation."),
    ("whisper_quiet", "clean_studio", "medium", "The security audit revealed three critical vulnerabilities in the legacy authentication service. We must patch them immediately without alerting external users."),
    ("whisper_quiet", "low_snr", "long", "Between you and me, the reason the vice president cancelled the roadmap review is because the preliminary third-quarter revenue numbers were significantly below the board's expectations. Keep this strictly confidential until the official investor relations release next Tuesday."),

    # 41-55: Conference Meetings
    ("conference_meeting", "clean_studio", "micro", "Welcome everyone to today's sync."),
    ("conference_meeting", "reverb", "short", "Today's agenda covers three primary topics: quarterly headcount, cloud infrastructure spend, and the product roadmap."),
    ("conference_meeting", "clean_studio", "medium", "First, Marcus will present the sales conversion metrics for the enterprise tier, followed by a twenty-minute question and answer session with the regional leads."),
    ("conference_meeting", "low_snr", "short", "Can everyone on the Zoom call please verify that you can see my shared presentation slides?"),
    ("conference_meeting", "compressed_mic", "medium", "The committee voted unanimously to approve the thirty-thousand-dollar budget expansion for user experience research and international usability testing."),
    ("conference_meeting", "ac_hum", "short", "Action items from last week's sync have all been resolved except for the third-party compliance review."),
    ("conference_meeting", "clean_studio", "long", "Thank you all for joining our annual strategic planning summit. Over the next two quarters, our core objective is establishing market leadership in autonomous developer tools. This requires three coordinated milestones: unifying our local offline speech models, accelerating cloud API inference under one second, and guaranteeing absolute zero data loss for enterprise users."),
    ("conference_meeting", "street_noise", "short", "Let us table this discussion for the breakout session tomorrow afternoon."),
    ("conference_meeting", "clean_studio", "micro", "Any further questions before we adjourn?"),
    ("conference_meeting", "reverb", "medium", "The marketing team reported a sixty-five percent increase in webinar signups following our targeted developer newsletter campaign last Thursday."),
    ("conference_meeting", "low_snr", "medium", "Please ensure that your sprint velocity estimates account for the upcoming company holiday on Friday. All pull requests must be merged by Wednesday noon."),
    ("conference_meeting", "clean_studio", "short", "We have invited two external advisors to review our data governance and privacy policies."),
    ("conference_meeting", "compressed_mic", "long", "Reviewing our operational key results for this quarter: product reliability reached ninety-nine point nine-five percent uptime, customer support resolution time dropped from four hours to forty-two minutes, and forty-five thousand active developers adopted our open-source framework across thirty countries."),
    ("conference_meeting", "ac_hum", "short", "Let's schedule a dedicated thirty-minute deep dive on this specific technical blocker."),
    ("conference_meeting", "clean_studio", "micro", "Meeting adjourned, thank you everyone."),

    # 56-70: Legal & Medical Terminology
    ("legal_medical", "clean_studio", "short", "The plaintiff alleges breach of contract under Section four of the Commercial Code."),
    ("legal_medical", "clean_studio", "medium", "The patient presented with acute hypertensive encephalopathy, elevated intracranial pressure, and bilateral papilledema, requiring intravenous labetalol administration."),
    ("legal_medical", "compressed_mic", "short", "Both parties mutually agree to indemnify and hold harmless the licensing distributor."),
    ("legal_medical", "low_snr", "medium", "Pharmacokinetic analysis demonstrated that the active drug metabolite reached peak serum concentration at approximately two point four hours post-oral administration."),
    ("legal_medical", "clean_studio", "micro", "Objection sustained, counsel may proceed."),
    ("legal_medical", "reverb", "short", "The deposee stated under oath that they had no prior knowledge of the patent infringement claim."),
    ("legal_medical", "ac_hum", "medium", "Histopathological examination of the tissue biopsy revealed non-caseating granulomas consistent with a systemic sarcoidosis diagnosis."),
    ("legal_medical", "clean_studio", "long", "In the matter of Smith versus Apex Technologies, the arbitral tribunal found that the intellectual property assignment clause in Exhibit B was legally enforceable. The defendant is hereby enjoined from reproducing, distributing, or commercializing the proprietary speech synthesis algorithms without prior written authorization."),
    ("legal_medical", "street_noise", "short", "The electrocardiogram demonstrated sinus tachycardia with non-specific ST-segment and T-wave abnormalities."),
    ("legal_medical", "clean_studio", "medium", "The settlement agreement stipulates that all claims shall be dismissed with prejudice, and each party shall bear its own legal fees."),
    ("legal_medical", "compressed_mic", "micro", "Prescribe metformin five hundred milligrams daily."),
    ("legal_medical", "low_snr", "short", "The contract contains an express force majeure clause excusing performance in cases of natural disasters."),
    ("legal_medical", "clean_studio", "long", "The patient underwent magnetic resonance imaging of the lumbar spine, which revealed a moderate L4-L5 disc protrusion causing mild neural foraminal narrowing and impingement on the traversing L5 nerve root. Conservative therapy comprising physical rehabilitation and non-steroidal anti-inflammatory medication was initiated."),
    ("legal_medical", "ac_hum", "short", "The affiant affirms that the statements contained herein are true and correct to the best of their knowledge."),
    ("legal_medical", "clean_studio", "micro", "Vital signs remain within normal limits."),

    # 71-85: Code Dictation
    ("code_dictation", "clean_studio", "micro", "git checkout -b feature/audio-benchmarks"),
    ("code_dictation", "clean_studio", "short", "SELECT user_id, email, created_at FROM users WHERE is_active = TRUE ORDER BY created_at DESC;"),
    ("code_dictation", "compressed_mic", "short", "npm install @tanstack/react-query lucide-react clsx tailwind-merge"),
    ("code_dictation", "low_snr", "medium", "def calculate_word_error_rate(reference: str, hypothesis: str) -> float: return round(edit_distance(reference, hypothesis) / len(reference.split()), 4)"),
    ("code_dictation", "clean_studio", "micro", "docker compose up -d --build"),
    ("code_dictation", "ac_hum", "short", "curl -X POST https://api.gemini.internal/v1/transcribe -H 'Authorization: Bearer SECRET' -d @audio.wav"),
    ("code_dictation", "reverb", "medium", "class AudioBufferPool: def __init__(self, max_capacity: int = 100): self.pool = collections.deque(maxlen=max_capacity)"),
    ("code_dictation", "clean_studio", "long", "const handleSubmit = async (event: React.FormEvent) => { event.preventDefault(); setLoading(true); try { const response = await fetch('/api/transcribe', { method: 'POST', body: formData }); const data = await response.json(); setTranscript(data.text); } catch (err) { setError(err.message); } finally { setLoading(false); } };"),
    ("code_dictation", "street_noise", "short", "pytest tests/ --cov=app --cov-report=term-missing -v"),
    ("code_dictation", "clean_studio", "micro", "git push origin main --force-with-lease"),
    ("code_dictation", "compressed_mic", "medium", "import sqlite3; conn = sqlite3.connect('benchmarks.db'); cursor = conn.cursor(); cursor.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, latency REAL);');"),
    ("code_dictation", "low_snr", "short", "kubectl get pods -n speech-services -l app=whisper-engine -o wide"),
    ("code_dictation", "clean_studio", "long", "version: '3.8'\nservices:\n  whisper:\n    image: faster-whisper:int8\n    ports:\n      - '8080:8080'\n    deploy:\n      resources:\n        reservations:\n          devices:\n            - driver: nvidia\n              count: 1\n              capabilities: [gpu]"),
    ("code_dictation", "ac_hum", "short", "cat << 'EOF' > /etc/systemd/system/geminiflow.service\n[Unit]\nDescription=Gemini Flow Daemon\nEOF"),
    ("code_dictation", "clean_studio", "micro", "cargo build --release --target x86_64-pc-windows-msvc"),

    # 86-95: Storytelling & Narratives
    ("storytelling", "clean_studio", "micro", "It all began on a stormy Tuesday evening."),
    ("storytelling", "reverb", "short", "We sat around the kitchen table, sketching the first prototype on the back of a paper napkin."),
    ("storytelling", "clean_studio", "medium", "The team worked through the night, fueled by cold coffee and relentless optimism, convinced that local speech recognition could finally match cloud intelligence."),
    ("storytelling", "low_snr", "short", "When the first automated test passed without an error, the entire room erupted in cheers."),
    ("storytelling", "street_noise", "medium", "Ten years ago, nobody believed that a language model could run inside a smartphone browser. Today, we execute billions of neural inferences on everyday consumer laptops without breaking a sweat."),
    ("storytelling", "clean_studio", "long", "In the early days of computing, voice recognition required soundproof acoustic chambers and refrigerator-sized mainframes. An operator had to pause between every single word, enunciating with deliberate mechanical cadence. Today, we stand in noisy streets, whispering into microscopic silicon sensors, and intelligent algorithms transcribe poetry, law, and code in fractions of a second."),
    ("storytelling", "compressed_mic", "short", "He closed his laptop, walked over to the window, and watched the sunrise over Silicon Valley."),
    ("storytelling", "ac_hum", "medium", "Every great engineering breakthrough begins with a frustrating bottleneck that someone refuses to accept as permanent."),
    ("storytelling", "clean_studio", "micro", "And that changed everything forever."),
    ("storytelling", "clean_studio", "long", "As the clock struck midnight before launch day, the continuous integration pipeline flashed green across all six hundred test suites. Three engineers who had spent six months redesigning the transcription pipeline high-fived in exhausted silence. They knew that tomorrow, tens of thousands of users would speak to their computers and feel like magic was truly real."),

    # 96-100: Multilingual Accents & International Dictation
    ("multilingual", "clean_studio", "micro", "Bonjour, comment allez-vous aujourd'hui?"),
    ("multilingual", "low_snr", "short", "The total shipment invoice was twelve thousand five hundred euros, payable via SEPA transfer to our Frankfurt headquarters."),
    ("multilingual", "clean_studio", "medium", "Our Tokyo development team confirmed that the yen currency formatting bug was resolved in release version two point four."),
    ("multilingual", "street_noise", "short", "Guten Tag, wir möchten das neue Sprachmodell heute Nachmittag testen."),
    ("multilingual", "clean_studio", "long", "From our engineering offices in Zurich, Bengaluru, and San Francisco, our distributed workforce collaborates across three time zones. We maintain localized language models supporting English, German, French, Spanish, Hindi, and Japanese, ensuring native pronunciation and punctuation across all enterprise applications.")
]

assert len(CORPUS) == 100, f"Expected 100 corpus entries, got {len(CORPUS)}"

# 100 Distinct Formatting Task Definitions
FORMATS = [
    {"id": 1, "name": "Verbatim Raw", "instruction": "Output the raw verbatim transcription exactly as spoken with no formatting or alterations."},
    {"id": 2, "name": "Professional Business Memo", "instruction": "Format this text into an executive business memo with TO, FROM, DATE, SUBJECT, and MEMORANDUM BODY sections."},
    {"id": 3, "name": "Bulleted Executive Summary", "instruction": "Format this text into a bulleted executive summary with Key Takeaways (•) and Action Items (•)."},
    {"id": 4, "name": "Grammar & Punctuation Auto-Repair", "instruction": "Correct all grammar, remove filler words (um, uh, like), fix verb tenses, and ensure flawless punctuation."},
    {"id": 5, "name": "Developer Technical Documentation", "instruction": "Format as developer technical documentation in clean Markdown with headers, code blocks, and parameter descriptions."},
    {"id": 6, "name": "Legal Deposition Format", "instruction": "Format into formal legal deposition transcript style with timestamps [00:00:00], speaker tags, and line numbers."},
    {"id": 7, "name": "Strict JSON Schema Output", "instruction": "Output strictly valid JSON matching schema: {\"transcript\": string, \"sentiment\": string, \"entities\": list, \"word_count\": int}."},
    {"id": 8, "name": "Meeting Minutes with Deadlines", "instruction": "Format into Meeting Minutes with Attendees, Discussion Topics, Decisions Made, and Action Items with Deadlines."},
    {"id": 9, "name": "Social Media Thread Format", "instruction": "Format as an engaging social media post / viral X thread with a strong hook, 3 numbered points, and 3 hashtags."},
    {"id": 10, "name": "Academic Formal Abstract", "instruction": "Format into a formal academic paper abstract with Background, Methods, Results, and Conclusion."},
    {"id": 11, "name": "Slack Direct Message", "instruction": "Format as a warm, concise Slack direct message using bullet points and professional emoji anchors."},
    {"id": 12, "name": "Customer Support Ticket", "instruction": "Format as a helpful customer support ticket resolution with empathetic greeting, step-by-step fix, and closing."},
    {"id": 13, "name": "Incident Post-Mortem RCA", "instruction": "Format as an engineering Root Cause Analysis (RCA) with Incident Summary, Root Cause, Impact, and Remediation Items."},
    {"id": 14, "name": "GitHub Pull Request Description", "instruction": "Format as a GitHub PR description with ## Summary of Changes, ## Motivation, ## Testing Steps, and [x] Checklist."},
    {"id": 15, "name": "Daily Standup Update", "instruction": "Format as an agile daily standup update with Yesterday's Accomplishments, Today's Focus, and Blockers."},
    {"id": 16, "name": "Product Requirements Document", "instruction": "Format as a PRD snippet with Problem Statement, Target User Story, and Acceptance Criteria."},
    {"id": 17, "name": "Press Release Announcement", "instruction": "Format as a corporate press release with FOR IMMEDIATE RELEASE, Dateline, Headline, Body, and Media Contact."},
    {"id": 18, "name": "Sales Call Email Follow-Up", "instruction": "Format as a high-conversion sales follow-up email with thank you, summary of pain points, and next steps call to action."},
    {"id": 19, "name": "YAML Configuration Schema", "instruction": "Convert the information into a valid YAML configuration schema with version, metadata, and spec fields."},
    {"id": 20, "name": "Markdown Table Structure", "instruction": "Structure the core entities and attributes of the text into a clean Markdown table with headers and pipe (|) delimiters."},
    {"id": 21, "name": "FAQ Q&A Format", "instruction": "Extract the core concepts into a Frequently Asked Questions (FAQ) format with Q: and A: pairs."},
    {"id": 22, "name": "Key-Value Dictionary", "instruction": "Extract key attributes from the speech into a clear Key: Value format, one attribute per line."},
    {"id": 23, "name": "Interview Candidate Assessment", "instruction": "Format as a hiring interview assessment with Candidate, Role, Key Strengths, Areas for Growth, and Recommendation."},
    {"id": 24, "name": "Concise One-Sentence TL;DR", "instruction": "Synthesize the entire text into a single, punchy TL;DR sentence of twenty-five words or fewer."},
    {"id": 25, "name": "Standard Operating Procedure (SOP)", "instruction": "Format as a Standard Operating Procedure (SOP) with Purpose, Scope, Prerequisites, and Numbered Procedure Steps."},
    {"id": 26, "name": "Security Advisory Bulletin", "instruction": "Format as a CVE-style security advisory bulletin with Title, Severity (Low/Med/High/Critical), Affected Component, and Mitigation."},
    {"id": 27, "name": "Sprint Retrospective Notes", "instruction": "Format as agile sprint retro notes with What Went Well (•), What Could Be Improved (•), and Action Items (•)."},
    {"id": 28, "name": "Board of Directors Brief", "instruction": "Format as an executive brief for the Board of Directors with Strategic Context, Financial Impact, and Decision Requested."},
    {"id": 29, "name": "Medical SOAP Note", "instruction": "Format into clinical SOAP note structure: Subjective (S), Objective (O), Assessment (A), and Plan (P)."},
    {"id": 30, "name": "Financial Earnings Summary", "instruction": "Format as a quarterly financial earnings recap with Revenue, Margin Highlights, Key Drivers, and FY Guidance."},
    {"id": 31, "name": "Podcast Episode Show Notes", "instruction": "Format as podcast show notes with Episode Title, Overview, Key Discussion Timestamps, and Guest/Resource Links."},
    {"id": 32, "name": "Formal Service Apology Letter", "instruction": "Format as a formal executive apology letter with sincere acknowledgment of error, root cause explanation, and remedy."},
    {"id": 33, "name": "Feature Flag Rollout Plan", "instruction": "Format as a software feature flag announcement with Flag Name, Rollout Percentage, Target Cohort, and Kill Switch Guide."},
    {"id": 34, "name": "Architecture Decision Record (ADR)", "instruction": "Format as an ADR with Title, Status (Proposed/Accepted), Context, Decision, and Consequences."},
    {"id": 35, "name": "Knowledge Base Troubleshooting", "instruction": "Format as a knowledge base article with Issue Description, Cause, and Step-by-Step Resolution."},
    {"id": 36, "name": "Cold Outreach Sales Email", "instruction": "Format as a personalized, punchy cold outreach email with hook, value proposition, and low-friction call to action."},
    {"id": 37, "name": "Weekly Status Report", "instruction": "Format as a weekly team status report with Key Wins, Work in Progress, Blockers/Risks, and Next Week's Priorities."},
    {"id": 38, "name": "Code Review Feedback", "instruction": "Format as constructive GitHub code review feedback with File, Line Context, Severity, Feedback, and Suggested Code Patch."},
    {"id": 39, "name": "Keep-a-Changelog Entry", "instruction": "Format into Keep a Changelog standard with ## [Unreleased] section containing Added, Changed, Fixed, or Removed."},
    {"id": 40, "name": "Strict XML Schema Output", "instruction": "Output strictly valid XML matching schema: <report><transcript>...</transcript><category>...</category><metrics>...</metrics></report>."},
    {"id": 41, "name": "Project Milestone Tracker", "instruction": "Format as a project tracker with Milestone Name, Owner, Due Date, Status (On Track/At Risk/Completed), and Notes."},
    {"id": 42, "name": "Pitch Deck Slide Outline", "instruction": "Format into a 3-slide pitch outline with Slide 1 (Problem), Slide 2 (Solution), and Slide 3 (Market Traction)."},
    {"id": 43, "name": "User Persona Profile", "instruction": "Format as a UX User Persona with Name/Title, Core Goals, Frustrations/Pain Points, and Preferred Tech Stack."},
    {"id": 44, "name": "Bug Triage Report", "instruction": "Format as a software bug report with Bug ID, Severity, Steps to Reproduce, Expected Behavior, and Actual Behavior."},
    {"id": 45, "name": "Customer Case Study", "instruction": "Format as a customer success case study with Customer Profile, The Challenge, The Solution, and Measurable Results."},
    {"id": 46, "name": "All-Hands Keynote Speech", "instruction": "Format as an inspiring CEO all-hands speech transcript with Opening Hook, Strategic Vision, Team Recognition, and Call to Action."},
    {"id": 47, "name": "REST API Endpoint Spec", "instruction": "Format as an OpenAPI REST endpoint specification with HTTP Method, Path, Request Parameters, and 200 OK Response schema."},
    {"id": 48, "name": "Non-Disclosure Agreement Summary", "instruction": "Format as a legal NDA summary with Disclosing Party, Receiving Party, Confidential Information Definition, and Term Length."},
    {"id": 49, "name": "New Hire Onboarding Checklist", "instruction": "Format as an employee onboarding checklist divided into Day 1 Tasks, Week 1 Milestones, and Month 1 Goals."},
    {"id": 50, "name": "Performance Review Self-Eval", "instruction": "Format as an annual performance review self-evaluation with Major Contributions, Overcoming Challenges, and Goals for Next Year."},
    {"id": 51, "name": "Customer Feedback Sentiment Log", "instruction": "Format into a feedback log with Raw Quote, Sentiment (Positive/Neutral/Negative), Key Themes, and Follow-Up Priority."},
    {"id": 52, "name": "Product Launch Announcement Email", "instruction": "Format as a marketing product launch email with bold Headline, New Capabilities (•), and Get Started Button."},
    {"id": 53, "name": "Risk Assessment Matrix", "instruction": "Format as a risk analysis with Risk Description, Likelihood (1-5), Severity (1-5), and Mitigation Strategy."},
    {"id": 54, "name": "DevOps Runbook Procedure", "instruction": "Format as an on-call DevOps runbook with Trigger Alert, Severity Level, Initial Triage Steps, and Escalation Path."},
    {"id": 55, "name": "Beginner Educational Tutorial", "instruction": "Format as a beginner-friendly tutorial with Conceptual Explanation, Real-World Analogy, Code Example, and Quick Quiz."},
    {"id": 56, "name": "Newsletter Curated Feature", "instruction": "Format as an email newsletter segment with Catchy Header, 3-Sentence Analytical Breakdown, and Read More Link."},
    {"id": 57, "name": "Executive Decision Memo", "instruction": "Format as an executive decision paper with Decision Required, Background Context, Options Considered, and Recommendation."},
    {"id": 58, "name": "Data Governance Policy Addendum", "instruction": "Format as a data governance policy with Data Classification Level, Retention Period, Encryption Requirement, and Audit Policy."},
    {"id": 59, "name": "Marketing Creative Brief", "instruction": "Format as an advertising creative brief with Campaign Objective, Target Demographic, Core Message, Tone, and Deliverables."},
    {"id": 60, "name": "Job Description Posting", "instruction": "Format as a high-impact job description with Role Title, Team Mission, Core Responsibilities, and Required Qualifications."},
    {"id": 61, "name": "Micro-Learning Flashcard", "instruction": "Format as an educational flashcard with Front (Prompt/Question) and Back (Key Concept + Memory Tip)."},
    {"id": 62, "name": "User Research Interview Notes", "instruction": "Format as user research notes with Participant ID, Key Quotes, Observed Behaviors, and UX Recommendations."},
    {"id": 63, "name": "Competitive Intelligence Brief", "instruction": "Format as a competitor intelligence brief with Competitor Name, Recent Move, Market Threat Level, and Counter-Strategy."},
    {"id": 64, "name": "App Store Release Notes", "instruction": "Format as consumer app store release notes with What's New in Version 3.0 and bulleted feature highlights with emojis."},
    {"id": 65, "name": "Infrastructure as Code HCL", "instruction": "Format the infrastructure resources discussed into clean Terraform HCL resource blocks."},
    {"id": 66, "name": "OKR Goal Template", "instruction": "Format into Objectives and Key Results (OKR) format with 1 Inspiring Objective and 3 Measurable Key Results with % targets."},
    {"id": 67, "name": "Privacy Policy Statement", "instruction": "Format as a formal GDPR/CCPA privacy policy statement with Information Collected, Legal Basis, and User Rights."},
    {"id": 68, "name": "Quarterly Budget Variance Report", "instruction": "Format as a financial budget variance report with Expense Category, Allocated Budget, Actual Spend, and Variance %."},
    {"id": 69, "name": "Hardware Benchmark Spec Sheet", "instruction": "Format as a hardware benchmark specification sheet with Component, Test Metric, Benchmark Score, and Delta vs Baseline."},
    {"id": 70, "name": "Gherkin BDD Feature File", "instruction": "Format into Gherkin BDD syntax with Feature:, Scenario:, Given, When, and Then statements."},
    {"id": 71, "name": "Cloud Status Page Update", "instruction": "Format as a public cloud status update with Component Affected, Status (Investigating/Identified/Resolved), and Timestamp."},
    {"id": 72, "name": "Sales Objection Handling Script", "instruction": "Format as a sales battlecard with Customer Objection, Root Concern, and Recommended Response Strategy."},
    {"id": 73, "name": "Event Logistics Invitation", "instruction": "Format as an executive event invitation with Event Name, Date & Time, Location/Link, Dress Code, and Agenda."},
    {"id": 74, "name": "Product Roadmap Epics Overview", "instruction": "Format into a product roadmap view with Now (In Progress), Next (Coming Soon), and Later (Future Vision) epics."},
    {"id": 75, "name": "Cloud Migration Strategy Plan", "instruction": "Format as a cloud migration plan with Workload Name, Current State, Target Cloud Architecture, and Migration Phases."},
    {"id": 76, "name": "Customer Offboarding Analysis", "instruction": "Format as customer churn analysis with Account Name, Churn Reason, Primary Pain Point, and Win-Back Eligibility."},
    {"id": 77, "name": "SQL DDL & Query Explanation", "instruction": "Format as SQL DDL/DML statements accompanied by a clean plain-English explanation of table relationships."},
    {"id": 78, "name": "Contract Milestone Payment Schedule", "instruction": "Format as a commercial contract payment schedule with Milestone Number, Deliverable Description, % Payment, and Target Date."},
    {"id": 79, "name": "Webinar Intro & Speaker Bio", "instruction": "Format as a webinar host script with Welcome Remarks, Housekeeping Notes, Topic Teaser, and Speaker Biography."},
    {"id": 80, "name": "WCAG Accessibility Audit", "instruction": "Format as an accessibility compliance report with WCAG Guideline (e.g. 1.4.3 Contrast), Conformance Level, Finding, and Remediation."},
    {"id": 81, "name": "Vendor Risk Assessment", "instruction": "Format as a third-party vendor review with Vendor Name, Service Provided, Security Risk Tier, and Compliance Status."},
    {"id": 82, "name": "Brand Voice & Tone Guidelines", "instruction": "Format as brand voice guidelines with Brand Attribute, Do (Positive Example), and Don't (Negative Example)."},
    {"id": 83, "name": "AI Ethics & Safety Audit", "instruction": "Format as an AI governance audit with Model Name, Fairness Check, Bias Mitigation, Privacy Guarantee, and Transparency Tier."},
    {"id": 84, "name": "Employee Recognition Kudos", "instruction": "Format as an authentic peer recognition message celebrating specific achievements and values demonstrated."},
    {"id": 85, "name": "Penetration Testing Finding", "instruction": "Format as a cybersecurity pen-test finding with Finding Title, Risk Rating, Vulnerability Description, and Proof of Concept."},
    {"id": 86, "name": "Customer Journey Touchpoint Map", "instruction": "Format as a customer journey map with Stage (Awareness/Consideration/Purchase), User Action, Emotional State, and Pain Point."},
    {"id": 87, "name": "Open-Source Contribution Guide", "instruction": "Format as an open-source CONTRIBUTING.md guide with Forking Instructions, Coding Standards, and Pull Request Guidelines."},
    {"id": 88, "name": "Disaster Recovery Playbook", "instruction": "Format as a disaster recovery playbook with Disaster Scenario, Recovery Time Objective (RTO), and Failover Execution Steps."},
    {"id": 89, "name": "Knowledge Transfer Handover", "instruction": "Format as a project handover doc with System Name, Repository Links, Key Team Contacts, and Known Technical Quirks."},
    {"id": 90, "name": "Email Subject Line Variations", "instruction": "Generate 5 distinct email subject line variations: 1. Curiosity Hook, 2. Urgent, 3. Benefit-Driven, 4. Direct, 5. Question."},
    {"id": 91, "name": "SEO Content Strategy Brief", "instruction": "Format as an SEO content brief with Target Keyword, Search Intent, Suggested Title, H2 Outline, and Target Word Count."},
    {"id": 92, "name": "Data Pipeline Architecture Blueprint", "instruction": "Format as a data pipeline architecture doc with Source Systems, Ingestion Method, Transformation Stage, Storage, and BI Consumers."},
    {"id": 93, "name": "Executive Elevator Pitch", "instruction": "Format as a crisp 30-second elevator pitch with Hook, Problem, Unique Value Proposition, and Call to Action."},
    {"id": 94, "name": "Conventional Commit Message", "instruction": "Format as a Conventional Commit message with type(scope): subject, detailed body, and BREAKING CHANGE footer if applicable."},
    {"id": 95, "name": "Legal Definitions Section", "instruction": "Format as a legal contract Definitions section with alphabetical defined terms in quotation marks followed by formal meanings."},
    {"id": 96, "name": "Usability Testing Moderator Script", "instruction": "Format as a user testing script with Welcome Script, Scenario Instructions, Think-Aloud Prompt, and Post-Task Question."},
    {"id": 97, "name": "Quarterly Customer Health Scorecard", "instruction": "Format as a Customer Success scorecard with Account Name, ARR, Health Rating (Green/Yellow/Red), and Retention Risk Plan."},
    {"id": 98, "name": "Machine Learning Model Card", "instruction": "Format as an ML Model Card with Model Architecture, Intended Use Cases, Training Data, Performance Metrics, and Known Limitations."},
    {"id": 99, "name": "Crisis Communications Press Statement", "instruction": "Format as a corporate crisis management statement with Factual Summary, Immediate Corrective Actions, Safety Reassurance, and Spokesperson."},
    {"id": 100, "name": "Synthesis Takeaway Matrix", "instruction": "Format into a comprehensive synthesis matrix with Dimension, Audio Fact Extracted, Practical Application, and Strategic Priority."}
]

assert len(FORMATS) == 100, f"Expected 100 formats, got {len(FORMATS)}"


def apply_acoustic_environment(audio: np.ndarray, sr: int, env: str) -> np.ndarray:
    """Applies realistic acoustic filtering and noise to simulate target environments."""
    if env == "clean_studio":
        return audio

    elif env == "low_snr":
        # Add white noise with SNR ~12 dB
        signal_power = np.mean(audio ** 2) + 1e-9
        noise_power = signal_power / (10 ** (12 / 10))
        noise = np.random.normal(0, np.sqrt(noise_power), len(audio))
        return np.clip(audio + noise, -1.0, 1.0)

    elif env == "street_noise":
        # Low frequency rumble (30-150Hz) + occasional transient
        t = np.arange(len(audio)) / sr
        rumble = 0.04 * np.sin(2 * np.pi * 45 * t) + 0.03 * np.sin(2 * np.pi * 85 * t)
        b, a = scipy.signal.butter(2, 200 / (sr / 2), btype='low')
        filtered_noise = scipy.signal.lfilter(b, a, np.random.normal(0, 0.08, len(audio)))
        return np.clip(audio * 0.9 + rumble + filtered_noise, -1.0, 1.0)

    elif env == "ac_hum":
        # 60Hz and 120Hz electrical hum + gentle air hiss
        t = np.arange(len(audio)) / sr
        hum = 0.035 * np.sin(2 * np.pi * 60 * t) + 0.015 * np.sin(2 * np.pi * 120 * t)
        hiss = np.random.normal(0, 0.01, len(audio))
        return np.clip(audio * 0.92 + hum + hiss, -1.0, 1.0)

    elif env == "reverb":
        # Room impulse response simulation with exponential decay
        decay_time = 0.25  # 250ms RT60
        decay_samples = int(decay_time * sr)
        t = np.arange(decay_samples) / sr
        impulse = np.exp(-3 * t / decay_time) * (np.random.rand(decay_samples) * 2 - 1)
        impulse[0] = 1.0  # Direct sound
        impulse = impulse / np.sum(np.abs(impulse))
        reverbed = scipy.signal.fftconvolve(audio, impulse, mode='full')[:len(audio)]
        return np.clip(reverbed, -1.0, 1.0)

    elif env == "compressed_mic":
        # Bandpass telephone/mic filter 300Hz - 3400Hz + gentle saturation
        b, a = scipy.signal.butter(3, [300 / (sr / 2), 3400 / (sr / 2)], btype='bandpass')
        filtered = scipy.signal.lfilter(b, a, audio)
        # Soft clipping / saturation
        saturated = np.tanh(filtered * 1.5)
        return np.clip(saturated, -1.0, 1.0)

    return audio


def build_dataset():
    print(f"[{time.strftime('%H:%M:%S')}] Starting generation of 100 Benchmark Audio Samples & Manifests...")
    
    # Initialize SAPI Voice Synthesizer
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    temp_wav = Path(tempfile.gettempdir()) / "temp_sapi_synth.wav"

    manifest = []
    t_start = time.time()

    for idx, (speech_type, env, dur_class, spoken_text) in enumerate(CORPUS, start=1):
        sample_id = f"{idx:03d}"
        wav_filename = f"sample_{sample_id}.wav"
        gt_filename = f"ground_truth_{sample_id}.txt"

        wav_path = AUDIO_DIR / wav_filename
        gt_path = GT_DIR / gt_filename

        # Write Ground Truth Reference Text
        with open(gt_path, "w", encoding="utf-8") as f:
            f.write(spoken_text.strip() + "\n")

        # Synthesize audio with SAPI
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(str(temp_wav), 3, False)
        voice.AudioOutputStream = stream
        
        # Adjust rate for rapid casual
        if speech_type == "rapid_casual":
            voice.Rate = 2
        elif speech_type == "whisper_quiet":
            voice.Rate = -1
            voice.Volume = 50
        else:
            voice.Rate = 0
            voice.Volume = 100

        voice.Speak(spoken_text)
        stream.Close()

        # Read back synthesized audio, resample to 16kHz mono float32
        data, original_sr = sf.read(str(temp_wav))
        if data.ndim > 1:
            data = data.mean(axis=1)

        target_sr = 16000
        if original_sr != target_sr:
            num_samples = int(len(data) * target_sr / original_sr)
            data = scipy.signal.resample(data, num_samples)

        # Apply acoustic environment filter
        data = apply_acoustic_environment(data, target_sr, env)

        # Scale and save as standard 16-bit PCM WAV
        sf.write(str(wav_path), data, target_sr, subtype='PCM_16')
        actual_duration = round(len(data) / target_sr, 2)

        format_item = FORMATS[idx - 1]

        manifest_item = {
            "sample_id": idx,
            "sample_str_id": sample_id,
            "audio_file": wav_filename,
            "audio_path": str(wav_path),
            "ground_truth_file": gt_filename,
            "ground_truth_path": str(gt_path),
            "duration_sec": actual_duration,
            "duration_class": dur_class,
            "speech_type": speech_type,
            "acoustic_environment": env,
            "verbatim_text": spoken_text,
            "paired_format_id": format_item["id"],
            "paired_format_name": format_item["name"],
            "format_instruction": format_item["instruction"]
        }
        manifest.append(manifest_item)

        if idx % 20 == 0 or idx == 1 or idx == 100:
            print(f"  Generated [{idx:03d}/100] {wav_filename} ({actual_duration:.1f}s, {speech_type}, {env})")

    if temp_wav.exists():
        try:
            temp_wav.unlink()
        except Exception:
            pass

    # Save manifest.json
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Save formats_manifest.json
    with open(FORMATS_PATH, "w", encoding="utf-8") as f:
        json.dump(FORMATS, f, indent=2)

    print(f"\n[{time.strftime('%H:%M:%S')}] SUCCESS: 100 Audio Samples & Formats Manifests fully built in {time.time() - t_start:.2f}s.")
    print(f"  Audio Directory: {AUDIO_DIR}")
    print(f"  Ground Truth:    {GT_DIR}")
    print(f"  Manifest:        {MANIFEST_PATH}")
    print(f"  Formats:         {FORMATS_PATH}")
    return manifest


if __name__ == "__main__":
    build_dataset()
