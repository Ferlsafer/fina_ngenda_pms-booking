#!/usr/bin/env python3

# PDF creator for API documentation using weasyprint
# This script creates a PDF version of the API documentation

def create_pdf():
    try:
        import weasyprint
    except ImportError:
        print("❌ weasyprint not available. Creating PDF with alternative method...")
        create_simple_pdf()
        return

    # Read HTML file
    with open('HMS_API_Documentation.html', 'r') as f:
        html_content = f.read()

    # Create PDF
    pdf_doc = weasyprint.HTML(string=html_content)
    pdf_doc.write_pdf('HMS_API_Documentation.pdf')
    
    print('✅ PDF documentation created successfully: HMS_API_Documentation.pdf')

def create_simple_pdf():
    """Create a simple text-based PDF if weasyprint is not available"""
    
    # Read the markdown files
    with open('API_DOCUMENTATION.md', 'r') as f:
        api_doc = f.read()

    with open('SAMPLE_OUTPUTS.md', 'r') as f:
        samples = f.read()

    # Create a simple text document
    text_content = f'''HMS FINALE - API DOCUMENTATION
{'=' * 60}

Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{api_doc}

{'=' * 60}

SAMPLE API OUTPUTS
{'=' * 60}

{samples}

{'=' * 60}
END OF DOCUMENT
'''

    # Save as text file (can be converted to PDF manually)
    with open('HMS_API_Documentation.txt', 'w') as f:
        f.write(text_content)
    
    print('✅ Text documentation created: HMS_API_Documentation.txt')
    print('📄 You can convert this to PDF using any online converter or LibreOffice')

if __name__ == '__main__':
    create_pdf()
