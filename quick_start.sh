#!/bin/bash
# =============================================================================
# MCP AGENT VULNERABILITY SCANNER - QUICK START SCRIPT
# =============================================================================
# This script sets up and starts the entire scanner system
# Run this script to get everything running in one go
#
# Usage:
#   bash quick_start.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}MCP AGENT VULNERABILITY SCANNER - QUICK START${NC}"
echo -e "${BLUE}========================================================${NC}"
echo ""

# Step 1: Check Python
echo -e "${YELLOW}Step 1: Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
echo ""

# Step 2: Create virtual environment
echo -e "${YELLOW}Step 2: Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi
echo ""

# Step 3: Activate virtual environment
echo -e "${YELLOW}Step 3: Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${YELLOW}Step 4: Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.py
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 5: Verify installation
echo -e "${YELLOW}Step 5: Verifying installation...${NC}"
if python verify_setup.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Installation verified${NC}"
else
    echo -e "${RED}✗ Installation verification failed${NC}"
    echo "Run: python verify_setup.py"
    exit 1
fi
echo ""

# Step 6: Display next steps
echo -e "${BLUE}========================================================${NC}"
echo -e "${GREEN}✓ SETUP COMPLETE!${NC}"
echo -e "${BLUE}========================================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Start the server:"
echo -e "   ${GREEN}uvicorn app.main:app --reload${NC}"
echo ""
echo "2. In another terminal, activate venv and run tests:"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "   ${GREEN}python test_runner.py${NC}"
echo ""
echo "3. View API documentation:"
echo -e "   ${GREEN}curl http://localhost:8000/api/v1/scan/health${NC}"
echo ""
echo "4. Scan a benchmark agent:"
echo -e "   ${GREEN}curl http://localhost:8000/api/v1/scan/scan_benchmark/web_scraper${NC}"
echo ""
echo "5. Scan all benchmarks:"
echo -e "   ${GREEN}curl http://localhost:8000/api/v1/scan/scan_all_benchmarks${NC}"
echo ""
echo "6. Read the documentation:"
echo -e "   ${GREEN}cat API_DOCUMENTATION.md${NC}"
echo ""
echo -e "${BLUE}========================================================${NC}"
echo -e "For detailed setup guide, see: SETUP_GUIDE.md"
echo -e "For API reference, see: API_DOCUMENTATION.md"
echo -e "${BLUE}========================================================${NC}"
