# Processing Templates

This directory contains custom processing templates for different source types.

## Template Types

- **XML Templates** - Custom processing rules for specific XML formats
- **PDF Templates** - Processing configurations for PDF sources
- **DOCX Templates** - Word document processing templates

## Usage

```bash
# Use custom template for processing
python pipeline_manager.py --stage chunk --source filename.xml --template templates/custom_xml_template.yaml
```

## Template Format

Templates should be in YAML format and specify:
- Source type identification
- Custom chunking rules
- Metadata extraction patterns
- Structure path generation rules
