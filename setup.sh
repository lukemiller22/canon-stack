#!/bin/bash
# Setup script for Theological Text Processing Pipeline

echo "Setting up Theological Text Processing Pipeline..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Create processing directory structure if it doesn't exist
if [ ! -d "theological_processing" ]; then
    echo "Creating processing directory structure..."
    mkdir -p theological_processing/{01_sources,02_chunked,03_annotated,04_complete,05_deployed,metadata,logs,templates,rejected}
fi

# Test pipeline initialization
echo "Testing pipeline initialization..."
python -c "from pipeline_manager import TheologicalProcessingPipeline; pipeline = TheologicalProcessingPipeline('./theological_processing'); print('✓ Pipeline ready!')"

echo ""
echo "Setup complete! To use the pipeline:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Check status: python pipeline_manager.py --stage status"
echo "3. Process files: python pipeline_manager.py --stage chunk --source filename.xml"
echo ""
echo "See theological_processing/README.md for detailed usage instructions."
