from weasyprint import HTML
import json
import os

def generate_pdf_report(summary_path):
    if not os.path.exists(summary_path):
        print(f"File {summary_path} not found.")
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    filename = os.path.splitext(summary_path)[0]
    title = f"MWE Summary Report: {summary.get('file', 'Batch')}"

    content = f'''
    <html>
    <head><style>
    body {{ font-family: Arial; padding: 20px; }}
    h1 {{ color: #2c3e50; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    td, th {{ border: 1px solid #ccc; padding: 8px; }}
    th {{ background: #f4f4f4; }}
    </style></head>
    <body>
    <h1>{title}</h1>
    <p><b>Total MWEs:</b> {summary['total_spans']}<br>
    <b>Average Confidence:</b> {summary['average_confidence']}</p>
    <h2>Span Type Counts</h2>
    <table>
    <tr><th>Type</th><th>Count</th></tr>
    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in summary["span_type_counts"].items())}
    </table>
    </body></html>
    '''

    HTML(string=content).write_pdf(f"{filename}_report.pdf")
    print(f"PDF report generated: {filename}_report.pdf")
