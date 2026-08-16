#!/bin/bash
echo "Setting up Amazon Feed Update Project environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Setup complete! Run ./run.sh to start the server."
