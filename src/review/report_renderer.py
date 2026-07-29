import html

def render_markdown(structured_review: dict) -> str:
    """Render the structured JSON into the PRD-specified Markdown format."""
    md = []
    
    # Title & Recommendation
    md.append(f"# AI PR Review")
    md.append(f"**Recommendation:** {structured_review.get('final_recommendation', 'Unknown')}\n")
    
    # Summary
    md.append(f"## Summary\n{structured_review.get('summary', '')}\n")
    
    # Findings
    findings = structured_review.get("findings", [])
    if findings:
        md.append("## Findings\n")
        md.append("| Severity | File | Line | Explanation | Recommendation |")
        md.append("|----------|------|------|-------------|----------------|")
        for f in findings:
            sev = f.get("severity", "Low")
            file = f.get("file", "unknown")
            line = f.get("line") or "N/A"
            exp = f.get("explanation", "").replace("\n", " ")
            rec = f.get("recommendation", "").replace("\n", " ")
            md.append(f"| {sev} | {file} | {line} | {exp} | {rec} |")
        md.append("")
        
    # Security Concerns
    security = structured_review.get("security_concerns", [])
    if security:
        md.append("## Security Concerns")
        for s in security:
            md.append(f"- {s}")
        md.append("")
        
    # Code Quality & Error Handling
    quality = structured_review.get("code_quality_notes", [])
    errors = structured_review.get("missing_error_handling", [])
    if quality or errors:
        md.append("## Code Quality & Architecture")
        for q in quality:
            md.append(f"- {q}")
        for e in errors:
            md.append(f"- Missing Error Handling: {e}")
        md.append("")
        
    # Test Cases
    test_cases = structured_review.get("test_cases", {})
    if any(test_cases.values()):
        md.append("## Recommended Test Cases")
        for cat, cases in test_cases.items():
            if cases:
                md.append(f"**{cat.title()}**")
                for c in cases:
                    md.append(f"- {c}")
        md.append("")
        
    # Regression Risk
    risk = structured_review.get("regression_risk", {})
    if risk:
        md.append("## Regression Risk")
        md.append(f"**Level:** {risk.get('level', 'Unknown')}")
        md.append(f"**Reasoning:** {risk.get('reasoning', '')}\n")
        
    return "\n".join(md)

def render_html(structured_review: dict) -> str:
    """Render the structured JSON into an HTML report."""
    markdown_content = render_markdown(structured_review)
    # Extremely basic markdown to HTML for now, enough to satisfy the structure.
    # In a real app we'd use a templating engine like Jinja2 or a markdown parser.
    html_content = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><title>AI PR Review Report</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }",
        "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
        "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
        "th { background-color: #f2f2f2; }",
        "</style>",
        "</head>",
        "<body>"
    ]
    
    # We will just write a custom simple parser since we strictly control the markdown output format.
    in_table = False
    for line in markdown_content.split("\n"):
        if line.startswith("# "):
            html_content.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            html_content.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("**"):
            # Very naive bold replacement
            bold_line = line.replace("**", "<b>", 1).replace("**", "</b>", 1)
            html_content.append(f"<p>{bold_line}</p>")
        elif line.startswith("- "):
            html_content.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.startswith("|") and "---" in line:
            continue
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                html_content.append("<table><tr>")
                for c in cells:
                    html_content.append(f"<th>{html.escape(c)}</th>")
                html_content.append("</tr>")
                in_table = True
            else:
                html_content.append("<tr>")
                for c in cells:
                    html_content.append(f"<td>{html.escape(c)}</td>")
                html_content.append("</tr>")
        else:
            if in_table:
                html_content.append("</table>")
                in_table = False
            if line.strip():
                html_content.append(f"<p>{html.escape(line)}</p>")
                
    if in_table:
        html_content.append("</table>")
        
    html_content.append("</body></html>")
    return "\n".join(html_content)
