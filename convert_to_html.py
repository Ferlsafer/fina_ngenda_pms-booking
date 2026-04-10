#!/usr/bin/env python3

# Simple HTML converter for API documentation
# This script creates an HTML version of the API documentation

def convert_markdown_to_html():
    # Read the markdown files
    with open('API_DOCUMENTATION.md', 'r') as f:
        api_doc = f.read()

    with open('SAMPLE_OUTPUTS.md', 'r') as f:
        samples = f.read()

    # Basic markdown conversion
    def simple_markdown(text):
        # Headers
        import re
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Code blocks
        text = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code>\2</code></pre>', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Lists
        lines = text.split('\n')
        in_list = False
        result = []
        
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                if line.strip():
                    result.append(f'<p>{line}</p>')
        
        if in_list:
            result.append('</ul>')
        
        return '\n'.join(result)

    # Convert both documents
    api_html = simple_markdown(api_doc)
    samples_html = simple_markdown(samples)

    # Create complete HTML document
    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HMS Finale API Documentation</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            background-color: #fff;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
            margin-bottom: 20px;
        }}
        
        h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        
        h3 {{
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        p {{
            margin-bottom: 15px;
        }}
        
        code {{
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            color: #e83e8c;
            font-size: 0.9em;
        }}
        
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #333;
            font-size: 0.9em;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            margin-left: 0;
            padding-left: 20px;
            color: #666;
            font-style: italic;
            margin: 20px 0;
        }}
        
        ul, ol {{
            margin: 20px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin-bottom: 5px;
        }}
        
        strong {{
            color: #2c3e50;
        }}
        
        em {{
            color: #666;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .section {{
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            background-color: #fafafa;
        }}
        
        .json-key {{ color: #d73502; font-weight: bold; }}
        .json-string {{ color: #0451a5; }}
        .json-number {{ color: #098658; }}
        .json-boolean {{ color: #0000ff; }}
        
        .endpoint {{
            background-color: #e8f5e8;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 4px solid #28a745;
        }}
        
        .method-get {{ border-left-color: #28a745; }}
        .method-post {{ border-left-color: #007bff; }}
        .method-put {{ border-left-color: #ffc107; }}
        .method-delete {{ border-left-color: #dc3545; }}
        
        @media print {{
            body {{ max-width: none; }}
            .section {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <h1>HMS Finale - Complete API Documentation</h1>
    
    <div class="section">
        <h2>Table of Contents</h2>
        <ul>
            <li><a href="#overview">System Overview</a></li>
            <li><a href="#tech-stack">Technical Stack</a></li>
            <li><a href="#architecture">System Architecture</a></li>
            <li><a href="#endpoints">API Endpoints</a></li>
            <li><a href="#business-logic">Key Business Logic</a></li>
            <li><a href="#samples">Sample API Outputs</a></li>
        </ul>
    </div>
    
    <div class="section">
        {api_html}
    </div>
    
    <div class="section">
        {samples_html}
    </div>
    
    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        <p>HMS Finale API Documentation - Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
</body>
</html>'''

    # Save HTML file
    with open('HMS_API_Documentation.html', 'w') as f:
        f.write(html_doc)

    print('✅ HTML documentation created successfully: HMS_API_Documentation.html')
    print('📄 You can open this file in any web browser')

if __name__ == '__main__':
    convert_markdown_to_html()
