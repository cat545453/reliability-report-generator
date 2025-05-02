#!/usr/bin/env python3
"""
Improved Reliability Report Generator with better error handling
and support for various status page formats
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta

# Import the updated scraper
from status_page_scraper_update import StatusPageScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReliabilityReportGenerator:
    """
    Improved generator with better error handling
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, output_dir: str = './output'):
        """
        Initialize the report generator.
        
        Args:
            openai_api_key: API key for OpenAI
            output_dir: Directory to save reports
        """
        # Import these here to avoid circular imports
        try:
            from incident_analyzer import IncidentAnalyzer
            from report_generator import ReportGenerator
        except ImportError as e:
            logger.error(f"Error importing required modules: {e}")
            raise
        
        self.scraper = StatusPageScraper(openai_api_key=openai_api_key)
        self.analyzer = IncidentAnalyzer(openai_api_key)
        self.report_generator = ReportGenerator(output_dir)
        
    def generate_report(self, 
                       company_name: str, 
                       status_page_url: str, 
                       peer_companies: Dict[str, str], 
                       timeframe_days: int = 90) -> Dict[str, str]:
        """
        Generate a reliability report with improved error handling.
        
        Args:
            company_name: Name of the target company
            status_page_url: URL of the target company's status page
            peer_companies: Dictionary mapping peer company names to their status page URLs
            timeframe_days: Number of days to analyze
            
        Returns:
            Dictionary with paths to the generated reports
        """
        logger.info(f"Starting reliability report generation for {company_name}")
        
        # 1. Scrape incident data for target company and peers
        all_incidents = []
        
        # Scrape target company first
        try:
            target_incidents = self.scraper.scrape_status_page(company_name, status_page_url, timeframe_days)
            if not target_incidents.empty:
                all_incidents.append(target_incidents)
        except Exception as e:
            logger.error(f"Error scraping incidents for {company_name}: {e}")
            # Create dummy data for the target company
            dummy_data = pd.DataFrame([{
                'company': company_name,
                'date': datetime.now(),
                'title': "Error retrieving incidents",
                'duration': "N/A",
                'summary': f"An error occurred while retrieving incidents: {str(e)}",
                'source_url': status_page_url,
                'category': "Error"
            }])
            all_incidents.append(dummy_data)
        
        # Scrape peer companies with robust error handling
        for peer_name, peer_url in peer_companies.items():
            try:
                peer_incidents = self.scraper.scrape_status_page(peer_name, peer_url, timeframe_days)
                if not peer_incidents.empty:
                    all_incidents.append(peer_incidents)
            except Exception as e:
                logger.error(f"Error scraping incidents for {peer_name}: {e}")
                # Create dummy data for this peer
                dummy_data = pd.DataFrame([{
                    'company': peer_name,
                    'date': datetime.now(),
                    'title': "Error retrieving incidents",
                    'duration': "N/A",
                    'summary': f"An error occurred while retrieving incidents: {str(e)}",
                    'source_url': peer_url,
                    'category': "Error"
                }])
                all_incidents.append(dummy_data)
        
        # Check if we have any incidents
        if not all_incidents:
            logger.warning("No incidents were found for any company")
            
            # Create a dummy DataFrame with company column and basic info
            dummy_data = []
            dummy_data.append({
                'company': company_name,
                'date': datetime.now(),
                'title': "No incidents found",
                'duration': "N/A",
                'summary': "No incident data could be extracted from any status page.",
                'category': "No Data"
            })
            
            for peer_name in peer_companies:
                dummy_data.append({
                    'company': peer_name,
                    'date': datetime.now(),
                    'title': "No incidents found",
                    'duration': "N/A",
                    'summary': "No incident data could be extracted from the status page.",
                    'category': "No Data"
                })
                
            combined_incidents = pd.DataFrame(dummy_data)
        else:
            try:
                # Combine all incidents into a single DataFrame
                combined_incidents = pd.concat(all_incidents, ignore_index=True)
            except Exception as e:
                logger.error(f"Error combining incidents: {e}")
                # Create a dummy DataFrame with error message
                combined_incidents = pd.DataFrame([{
                    'company': company_name,
                    'date': datetime.now(),
                    'title': "Error combining incidents",
                    'duration': "N/A",
                    'summary': f"An error occurred while combining incidents: {str(e)}",
                    'source_url': status_page_url,
                    'category': "Error"
                }])
        
        # Log basic statistics
        logger.info(f"Scraped {len(combined_incidents)} total incidents")
        
        # Show incidents by company (handle empty case)
        company_counts = combined_incidents['company'].value_counts().to_dict() if 'company' in combined_incidents.columns else {}
        logger.info(f"Incidents by company: {company_counts}")
        
        # 2. Analyze the incidents with error handling
        try:
            # Categorize incidents
            categorized_incidents = self.analyzer.categorize_incidents(combined_incidents)
            
            # Generate category descriptions
            category_info = self.analyzer.generate_category_descriptions(categorized_incidents)
            
            # Analyze trends
            trends = self.analyzer.analyze_trends(categorized_incidents)
            
            # Compare with peers
            comparison = self.analyzer.compare_with_peers(company_name, categorized_incidents)
        except Exception as e:
            logger.error(f"Error during incident analysis: {e}")
            # Set default values
            categorized_incidents = combined_incidents
            category_info = {"No Data": "No incident data available for analysis."}
            trends = {"message": "No trend data available due to analysis error."}
            comparison = {"message": "Peer comparison unavailable due to analysis error."}
        
        # 3. Generate the report with error handling
        try:
            report_path = self.report_generator.generate_report(
                target_company=company_name,
                timeframe_days=timeframe_days,
                incidents_df=categorized_incidents,
                category_info=category_info,
                trends=trends,
                comparison=comparison,
                output_file=f"{company_name.lower().replace(' ', '_')}_reliability_report"
            )
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            report_path = "./output/error_report.md"
            with open(report_path, 'w') as f:
                f.write(f"# Error Generating Reliability Report\n\nAn error occurred while generating the report: {str(e)}")
        
        # 4. Generate visualizations with error handling
        try:
            visualization_paths = self.report_generator.generate_visualizations(
                target_company=company_name,
                incidents_df=categorized_incidents,
                trends=trends
            )
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
            visualization_paths = {}
        
        # 5. Return paths to the generated reports
        return {
            'report': report_path,
            'spreadsheet': os.path.join(self.report_generator.output_dir, f"{company_name.lower().replace(' ', '_')}_reliability_report_incidents.xlsx"),
            'categories': os.path.join(self.report_generator.output_dir, f"{company_name.lower().replace(' ', '_')}_reliability_report_categories.xlsx"),
            'visualizations': visualization_paths
        }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate a reliability report for a SaaS company')
    
    parser.add_argument('--company', '-c', required=True,
                        help='Name of the target company')
    
    parser.add_argument('--url', '-u', required=True,
                        help='URL of the target company\'s status page')
    
    parser.add_argument('--peers', '-p', required=True,
                        help='Path to JSON file containing peer companies and their status page URLs')
    
    parser.add_argument('--timeframe', '-t', type=int, default=90,
                        help='Number of days to analyze (default: 90)')
    
    parser.add_argument('--output-dir', '-o', default='./output',
                        help='Directory to save the generated reports (default: ./output)')
    
    parser.add_argument('--openai-key', '-k',
                        help='OpenAI API key. If not provided, uses OPENAI_API_KEY environment variable')
    
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    return parser.parse_args()


def load_peer_companies(file_path: str) -> Dict[str, str]:
    """
    Load peer companies from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary mapping peer company names to their status page URLs
    """
    try:
        with open(file_path, 'r') as f:
            peers = json.load(f)
            
        # Validate the format
        if not isinstance(peers, dict):
            raise ValueError("Peer companies file must contain a JSON object")
            
        return peers
    except Exception as e:
        logger.error(f"Error loading peer companies from {file_path}: {e}")
        sys.exit(1)


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Load peer companies
    peer_companies = load_peer_companies(args.peers)
    logger.info(f"Loaded {len(peer_companies)} peer companies")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize the report generator
    try:
        generator = ReliabilityReportGenerator(
            openai_api_key=args.openai_key,
            output_dir=args.output_dir
        )
        
        # Generate the report
        report_paths = generator.generate_report(
            company_name=args.company,
            status_page_url=args.url,
            peer_companies=peer_companies,
            timeframe_days=args.timeframe
        )
        
        logger.info("Report generation completed successfully")
        logger.info(f"Report saved to: {report_paths['report']}")
        logger.info(f"Spreadsheet saved to: {report_paths['spreadsheet']}")
        logger.info(f"Categories saved to: {report_paths['categories']}")
        
        for viz_name, viz_path in report_paths.get('visualizations', {}).items():
            logger.info(f"Visualization '{viz_name}' saved to: {viz_path}")
            
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()