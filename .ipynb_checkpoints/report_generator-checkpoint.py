import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates a reliability report based on the analyzed incident data.
    """
    
    def __init__(self, output_dir: str = './output'):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory to save the generated reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_spreadsheet(self, incidents_df: pd.DataFrame, filename: str) -> str:
        """
        Generate a spreadsheet with all incidents.
        
        Args:
            incidents_df: DataFrame containing incident information
            filename: Base name for the output file
            
        Returns:
            Path to the generated spreadsheet
        """
        logger.info("Generating incidents spreadsheet")
        
        # Handle empty DataFrame
        if incidents_df.empty:
            empty_df = pd.DataFrame(columns=[
                'company', 'date', 'title', 'duration', 'summary', 'category', 'status', 'impact'
            ])
            
            excel_path = os.path.join(self.output_dir, f"{filename}.xlsx")
            empty_df.to_excel(excel_path, index=False, sheet_name="Incidents")
            
            csv_path = os.path.join(self.output_dir, f"{filename}.csv")
            empty_df.to_csv(csv_path, index=False)
            
            return excel_path
        
        # Ensure the incidents are sorted by date (most recent first)
        if 'date' in incidents_df.columns:
            incidents_df = incidents_df.sort_values('date', ascending=False)
        
        # Select relevant columns and rename them for clarity
        # Only include columns that exist in the DataFrame
        available_columns = ['company', 'date', 'title', 'duration', 'summary', 'category', 'status', 'impact']
        columns_to_select = [col for col in available_columns if col in incidents_df.columns]
        
        output_df = incidents_df[columns_to_select].copy()
        
        # Format the date column if it exists
        if 'date' in output_df.columns:
            output_df['date'] = output_df['date'].dt.strftime('%Y-%m-%d')
        
        # Save to Excel
        excel_path = os.path.join(self.output_dir, f"{filename}.xlsx")
        output_df.to_excel(excel_path, index=False, sheet_name="Incidents")
        
        # Also save as CSV for broader compatibility
        csv_path = os.path.join(self.output_dir, f"{filename}.csv")
        output_df.to_csv(csv_path, index=False)
        
        return excel_path
    
    def generate_category_report(self, category_info: Dict[str, Dict[str, Any]], filename: str) -> str:
        """
        Generate a report on incident categories.
        
        Args:
            category_info: Dictionary with category descriptions and examples
            filename: Base name for the output file
            
        Returns:
            Path to the generated report
        """
        logger.info("Generating category report")
        
        # Create a DataFrame for categories
        categories = []
        for category, info in category_info.items():
            example_title = "N/A"
            example_summary = "N/A"
            
            if 'examples' in info and info['examples']:
                example = info['examples'][0]
                if 'title' in example:
                    example_title = example['title']
                if 'summary' in example:
                    example_summary = example['summary']
            
            categories.append({
                'Category': category,
                'Description': info.get('description', ''),
                'Count': info.get('count', 0),
                'Example Title': example_title,
                'Example Summary': example_summary
            })
            
        categories_df = pd.DataFrame(categories)
        
        # If categories_df is empty, add a placeholder row
        if categories_df.empty:
            categories_df = pd.DataFrame([{
                'Category': 'No Data',
                'Description': 'No incident data was available for analysis.',
                'Count': 0,
                'Example Title': 'N/A',
                'Example Summary': 'N/A'
            }])
        
        # Sort by count (descending)
        if 'Count' in categories_df.columns:
            categories_df = categories_df.sort_values('Count', ascending=False)
        
        # Save to Excel
        excel_path = os.path.join(self.output_dir, f"{filename}.xlsx")
        categories_df.to_excel(excel_path, index=False, sheet_name="Categories")
        
        return excel_path
    
    def generate_report(self, 
                       target_company: str,
                       timeframe_days: int,
                       incidents_df: pd.DataFrame,
                       category_info: Dict[str, Dict[str, Any]],
                       trends: Dict[str, Any],
                       comparison: Dict[str, Any],
                       output_file: str = "reliability_report") -> str:
        """
        Generate a complete reliability report.
        
        Args:
            target_company: Name of the target company
            timeframe_days: Number of days in the analysis timeframe
            incidents_df: DataFrame with all incidents
            category_info: Dictionary with category information
            trends: Dictionary with trend information
            comparison: Dictionary with peer comparison information
            output_file: Name of the output file
            
        Returns:
            Path to the generated report
        """
        logger.info(f"Generating reliability report for {target_company}")
        
        # Check if there's a "No incidents found" message
        has_real_data = True
        if 'message' in trends:
            has_real_data = False
        elif incidents_df.empty or ('title' in incidents_df.columns and (incidents_df['title'] == "No incidents found").any()):
            has_real_data = False
        
        # Generate summary statistics
        target_incidents = incidents_df[incidents_df['company'] == target_company]
        total_incidents = len(target_incidents)
        
        if target_incidents.empty or not has_real_data:
            avg_duration = "N/A"
        else:
            # Try to calculate average duration if possible
            # This requires parsing the duration strings which can be complex
            # For now, we'll just report it as not calculated
            avg_duration = "Not calculated"
            
        # Start building the report in Markdown format
        report = f"""# Reliability Report: {target_company}

## Executive Summary

This report analyzes the reliability of {target_company} over the past {timeframe_days} days, comparing it with peer companies in the industry.

"""

        if not has_real_data:
            report += """
**Note**: We were unable to extract incident data from the status pages. This could be due to:
- The status pages use non-standard formats that our scraper couldn't process
- There were genuinely no incidents during the timeframe
- The status pages require authentication or have changed their URL structure

Please verify the status page URLs and try again, or consider extending the timeframe.

"""
        else:
            report += f"""
**Key Findings:**
- {target_company} experienced {total_incidents} incidents in the analyzed period
- Average incident duration: {avg_duration}
- Overall reliability trend: {trends.get('trend_direction', 'unknown')}
- Relative to peers: {comparison.get('relative_position', 'unknown')}

## Incident Statistics

Total incidents: {total_incidents}
Average incidents per week: {trends.get('avg_incidents_per_week', 0):.1f}

"""

            # Add top categories
            report += "### Top Incident Categories\n\n"
            top_categories = sorted(
                [(cat, info['count']) for cat, info in category_info.items() if len(target_incidents[target_incidents['category'] == cat]) > 0],
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            if top_categories:
                for category, count in top_categories:
                    category_percent = (count / total_incidents) * 100 if total_incidents > 0 else 0
                    report += f"- {category}: {count} incidents ({category_percent:.1f}%)\n"
            else:
                report += "No categorized incidents found.\n"
                
            report += "\n## Peer Comparison\n\n"
            
            # Add peer comparison
            if 'message' in comparison:
                report += f"{comparison['message']}\n\n"
            elif comparison.get('relative_position') == 'better':
                report += f"{target_company} had **fewer incidents** than the peer average "
                report += f"({comparison.get('target_incident_count', 0)} vs. {comparison.get('avg_peer_incident_count', 0):.1f} average).\n\n"
            else:
                report += f"{target_company} had **more incidents** than the peer average "
                report += f"({comparison.get('target_incident_count', 0)} vs. {comparison.get('avg_peer_incident_count', 0):.1f} average).\n\n"
                
            # Areas where target company is doing better
            report += "### Strengths\n\n"
            better_cats = comparison.get('better_categories', [])
            if better_cats:
                report += f"{target_company} had fewer incidents than peers in these categories:\n\n"
                for category in better_cats[:3]:  # Top 3
                    report += f"- {category}\n"
            else:
                report += "No categories where the company is outperforming peers.\n"
                
            # Areas where target company needs improvement
            report += "\n### Areas for Improvement\n\n"
            worse_cats = comparison.get('worse_categories', [])
            if worse_cats:
                report += f"{target_company} had more incidents than peers in these categories:\n\n"
                for category in worse_cats[:3]:  # Top 3
                    report += f"- {category}\n"
            else:
                report += "No categories where the company is underperforming peers.\n"
                
            # Add category breakdown
            report += "\n## Incident Categories\n\n"
            
            for category, info in sorted(category_info.items(), key=lambda x: x[1]['count'], reverse=True):
                target_count = len(target_incidents[target_incidents['category'] == category])
                if target_count > 0:
                    report += f"### {category}\n\n"
                    report += f"{info['description']}\n\n"
                    report += f"**Count:** {target_count} incidents\n\n"
                    
                    if info['examples'] and 'title' in info['examples'][0]:
                        report += "**Example:**\n\n"
                        example = info['examples'][0]
                        report += f"*{example['title']}*\n\n"
                        if 'summary' in example:
                            report += f"{example['summary']}\n\n"
        
        # Save the report
        report_path = os.path.join(self.output_dir, f"{output_file}.md")
        
        with open(report_path, 'w') as f:
            f.write(report)
            
        logger.info(f"Report saved to {report_path}")
        
        # Generate the spreadsheet and category report
        spreadsheet_path = self.generate_spreadsheet(incidents_df, f"{output_file}_incidents")
        category_report_path = self.generate_category_report(category_info, f"{output_file}_categories")
        
        logger.info(f"Spreadsheet saved to {spreadsheet_path}")
        logger.info(f"Category report saved to {category_report_path}")
        
        return report_path
    
    def generate_visualizations(self, 
                               target_company: str,
                               incidents_df: pd.DataFrame,
                               trends: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate visualizations for the report.
        
        Args:
            target_company: Name of the target company
            incidents_df: DataFrame with all incidents
            trends: Dictionary with trend information
            
        Returns:
            Dictionary mapping visualization names to file paths
        """
        logger.info("Generating visualizations")
        
        visualization_paths = {}
        
        # Check if we have real data to visualize
        if incidents_df.empty or 'message' in trends:
            logger.warning("No incident data to visualize")
            return visualization_paths
        
        # Set the plotting style
        plt.style.use('ggplot')
        sns.set_palette("colorblind")
        
        # 1. Incidents over time
        if 'incidents_by_week' in trends and trends['incidents_by_week']:
            try:
                plt.figure(figsize=(10, 6))
                incidents_by_week = pd.DataFrame(trends['incidents_by_week'])
                if not incidents_by_week.empty and 'year_week' in incidents_by_week.columns and 'count' in incidents_by_week.columns:
                    plt.bar(incidents_by_week['year_week'], incidents_by_week['count'])
                    plt.title(f'Incidents Over Time')
                    plt.xlabel('Week')
                    plt.ylabel('Number of Incidents')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    time_plot_path = os.path.join(self.output_dir, f"{target_company}_incidents_over_time.png")
                    plt.savefig(time_plot_path)
                    plt.close()
                    
                    visualization_paths['incidents_over_time'] = time_plot_path
            except Exception as e:
                logger.error(f"Error generating incidents over time visualization: {e}")
            
        # 2. Incidents by category
        target_incidents = incidents_df[incidents_df['company'] == target_company]
        if not target_incidents.empty and 'category' in target_incidents.columns:
            try:
                plt.figure(figsize=(10, 6))
                category_counts = target_incidents['category'].value_counts()
                if not category_counts.empty:
                    category_counts.plot(kind='bar')
                    plt.title(f'Incidents by Category - {target_company}')
                    plt.xlabel('Category')
                    plt.ylabel('Number of Incidents')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    category_plot_path = os.path.join(self.output_dir, f"{target_company}_incidents_by_category.png")
                    plt.savefig(category_plot_path)
                    plt.close()
                    
                    visualization_paths['incidents_by_category'] = category_plot_path
            except Exception as e:
                logger.error(f"Error generating incidents by category visualization: {e}")
            
        # 3. Company comparison
        if 'incidents_by_company' in trends and trends['incidents_by_company']:
            try:
                plt.figure(figsize=(10, 6))
                company_counts = pd.DataFrame(trends['incidents_by_company'])
                if not company_counts.empty and 'company' in company_counts.columns and 'count' in company_counts.columns:
                    sns.barplot(x='company', y='count', data=company_counts)
                    plt.title('Incidents by Company')
                    plt.xlabel('Company')
                    plt.ylabel('Number of Incidents')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    company_plot_path = os.path.join(self.output_dir, f"company_comparison.png")
                    plt.savefig(company_plot_path)
                    plt.close()
                    
                    visualization_paths['company_comparison'] = company_plot_path
            except Exception as e:
                logger.error(f"Error generating company comparison visualization: {e}")
            
        return visualization_paths