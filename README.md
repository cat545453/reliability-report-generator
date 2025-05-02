AI Reliability Report Generator
This project creates automated reliability reports for enterprise SaaS companies by analyzing their status pages and comparing incident patterns against peer companies.
Overview
The AI Reliability Report Generator extracts incident data from status pages, categorizes incidents using AI, identifies trends, and generates comprehensive reports with visualizations. It enables companies to benchmark their reliability against competitors and identify areas for improvement.
Features

Status Page Scraping: Extracts incident data from company status pages
AI-Powered Categorization: Uses OpenAI to intelligently categorize incidents
Peer Comparison: Compares reliability metrics against peer companies
Trend Analysis: Identifies patterns and trends in incident occurrence
Comprehensive Reporting: Generates detailed reports with visualizations
Flexible Configuration: Supports multiple status page formats

Installation
bash# Clone the repository
git clone https://github.com/yourusername/reliability-report-generator.git
cd reliability-report-generator

# Set up a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here  # On Windows: set OPENAI_API_KEY=your-api-key-here
Usage
Command Line Interface
bashpython cli.py --company "New Relic" --url "https://status.newrelic.com/history" --peers peer_companies.json --timeframe 90
Arguments

--company, -c: Name of the target company
--url, -u: URL of the target company's status page
--peers, -p: Path to JSON file with peer companies and their status page URLs
--timeframe, -t: Number of days to analyze (default: 90)
--output-dir, -o: Directory to save reports (default: ./output)
--openai-key, -k: OpenAI API key (otherwise uses OPENAI_API_KEY environment variable)
--debug: Enable debug logging

Sample Peer Companies JSON
json{
  "MongoDB": "https://status.mongodb.com/history",
  "Snowflake": "https://status.snowflake.com/history",
  "Confluent": "https://status.confluent.cloud/history",
  "DigitalOcean": "https://status.digitalocean.com/history",
  "Box": "https://status.box.com/history"
}
