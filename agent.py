import os
from groq import Groq
from tools import parse_log, check_upstream, suggest_fix

def run_agent(log_text: str):

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def add_step(title, content):
        return {"title": title, "content": content}

    yield add_step("Parsing log", "Reading the raw log and extracting structured information...")
    parsed = parse_log(log_text)
    yield add_step(
        "Log parsed",
        f"Error type detected: **{parsed['error_type']}**\n\nPipeline: {parsed['pipeline'] or 'not specified'}\n\nTimestamp: {parsed['timestamp'] or 'not found'}"
    )

    yield add_step("Checking upstream", "Looking for anomalies in upstream systems...")
    upstream = check_upstream(parsed["error_type"])
    yield add_step(
        "Upstream check complete",
        f"Status: **{upstream['status']}**\n\nSystem: {upstream['upstream_system']}\n\nFinding: {upstream['finding']}"
    )

    yield add_step("AI reasoning", "AI is analyzing the log and upstream findings...")
    prompt = "You are a senior data engineer diagnosing a pipeline failure.\n\nRaw log:\n" + log_text + "\n\nParsed error type: " + parsed["error_type"] + "\n\nUpstream finding: " + upstream["finding"] + "\n\nIn 3-4 sentences explain the root cause and urgency."
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    root_cause = response.choices[0].message.content
    yield add_step("Root cause identified", root_cause)

    yield add_step("Generating fix", "Looking up the best fix and code snippet...")
    fix = suggest_fix(parsed["error_type"], upstream["finding"])
    yield add_step(
        "Fix ready",
        f"Confidence: **{fix['confidence']}%**\n\n**What to do:** {fix['fix_summary']}\n\n**Prevention:** {fix['prevention']}"
    )

    yield add_step("Validating diagnosis", "Double-checking before surfacing to engineer...")
    val_prompt = "Pipeline failed: " + log_text + "\nDiagnosis: " + parsed["error_type"] + "\nFix: " + fix["fix_summary"] + "\nIn one sentence, confirm if correct."
    val_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": val_prompt}],
        max_tokens=150
    )
    yield add_step("Diagnosis validated", val_response.choices[0].message.content)

    yield {
        "title": "DONE",
        "content": "Agent completed diagnosis.",
        "result": {
            "error_type": parsed["error_type"],
            "root_cause": root_cause,
            "fix_summary": fix["fix_summary"],
            "code": fix["code"],
            "confidence": fix["confidence"],
            "prevention": fix["prevention"],
            "upstream": upstream["finding"]
        }
    }
