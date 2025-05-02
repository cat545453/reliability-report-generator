This repo is designed to automate the generation of reliability reports by aggregating and analyzing incident data from various sources. Here's a concise breakdown of its core components and the techniques:

1. **`status_page_scraper_update.py`**: This script employs web scraping techniques to extract incident data from public status pages. By parsing HTML content, it retrieves relevant information such as incident dates, durations, and descriptions, serving as the foundational data source for the analysis pipeline.

2. **`snowflake_scraper.py`**: Utilizing Snowflake's Python connector, this module connects to a Snowflake data warehouse to fetch structured incident logs. It executes SQL queries to retrieve data, ensuring seamless integration with enterprise-level data storage solutions.

3. **`incident_analyzer.py`**: This component processes the collected incident data, calculating metrics like Mean Time Between Failures (MTBF) and Mean Time To Recovery (MTTR). It leverages statistical analysis to identify patterns and trends, providing insights into system reliability over time.

4. **`report_generator.py`**: Responsible for compiling the analyzed data into comprehensive reports, this script formats the findings into readable documents, potentially in formats like PDF or HTML. It ensures that the insights are presented in a clear and accessible manner for stakeholders.

5. **`improved_main.py`**: Serving as the orchestrator, this main script coordinates the execution of the scraping, analysis, and reporting modules. It defines the workflow sequence, handles exceptions, and ensures that each component interacts seamlessly within the pipeline.

6. **`peer_companies.json`**: This JSON file contains a list of peer companies, likely used for benchmarking purposes. By comparing incident metrics across similar organizations, the tool can contextualize reliability performance within the industry landscape.

## 🚀 Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/reliability-report-generator.git
cd reliability-report-generator

# Set up a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here  # On Windows: set OPENAI_API_KEY=your-api-key-here```



