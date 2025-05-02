import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SnowflakeStatusScraper:
    """
    A class to scrape and analyze Snowflake status data from their API.
    """
    
    def __init__(self, days_lookback: int = 180):
        """
        Initialize the scraper with configuration parameters.
        
        Args:
            days_lookback: Number of days to look back for incident data
        """
        self.days_lookback = days_lookback
        self.base_url = "https://status.snowflake.com/api/v2"
        self.summary_endpoint = f"{self.base_url}/summary.json"
        self.incidents_endpoint = f"{self.base_url}/incidents.json"
        self.components_endpoint = f"{self.base_url}/components.json"
        self.headers = {
            "User-Agent": "Reliability-Report-Tool/1.0",
            "Accept": "application/json"
        }
        
    def fetch_data(self, url: str) -> Dict:
        """
        Fetch data from the specified URL with retry logic.
        
        Args:
            url: URL to fetch data from
            
        Returns:
            JSON response as a dictionary
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch data from {url} after {max_retries} attempts")
                    raise
    
    def get_current_status(self) -> Dict:
        """
        Get the current status of all Snowflake components.
        
        Returns:
            Dictionary containing current status information
        """
        try:
            data = self.fetch_data(self.summary_endpoint)
            return {
                'status': data.get('status', {}),
                'components': data.get('components', []),
                'incidents': data.get('incidents', []),
                'scheduled_maintenances': data.get('scheduled_maintenances', [])
            }
        except Exception as e:
            logger.error(f"Error fetching current status: {str(e)}")
            return {'status': {}, 'components': [], 'incidents': [], 'scheduled_maintenances': []}
    
    def get_historical_incidents(self) -> List[Dict]:
        """
        Get historical incidents from Snowflake's API.
        
        Returns:
            List of incident dictionaries
        """
        try:
            # Set up date range parameters if the API supports it
            # Note: The actual API might not support date filtering directly
            incidents = self.fetch_data(self.incidents_endpoint)
            
            # Filter incidents based on date if needed
            cutoff_date = datetime.now() - timedelta(days=self.days_lookback)
            
            # Format date strings from API
            filtered_incidents = []
            for incident in incidents.get('incidents', []):
                try:
                    created_at = datetime.fromisoformat(incident.get('created_at', '').replace('Z', '+00:00'))
                    if created_at >= cutoff_date:
                        filtered_incidents.append(incident)
                except ValueError:
                    # If date parsing fails, include the incident anyway
                    filtered_incidents.append(incident)
            
            return filtered_incidents
        except Exception as e:
            logger.error(f"Error fetching historical incidents: {str(e)}")
            return []
    
    def get_component_details(self) -> List[Dict]:
        """
        Get details of all components monitored by Snowflake.
        
        Returns:
            List of component dictionaries
        """
        try:
            components_data = self.fetch_data(self.components_endpoint)
            return components_data.get('components', [])
        except Exception as e:
            logger.error(f"Error fetching component details: {str(e)}")
            return []
    
    def analyze_reliability(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyze the reliability of Snowflake components.
        
        Returns:
            Tuple containing:
            - DataFrame with component reliability metrics
            - DataFrame with incident details
        """
        # Get current status and components
        status_data = self.get_current_status()
        components = status_data['components']
        
        # Get historical incidents
        incidents = self.get_historical_incidents()
        
        # Create component reliability dataframe
        component_data = []
        for component in components:
            component_data.append({
                'name': component.get('name', 'Unknown'),
                'group': component.get('group', False),
                'status': component.get('status', 'unknown'),
                'updated_at': component.get('updated_at', ''),
                'group_id': component.get('group_id', None),
                'description': component.get('description', '')
            })
        
        component_df = pd.DataFrame(component_data)
        
        # Create incidents dataframe
        incident_data = []
        for incident in incidents:
            # Extract incident updates
            updates = incident.get('incident_updates', [])
            latest_update = updates[0] if updates else {}
            
            incident_data.append({
                'name': incident.get('name', 'Unknown Incident'),
                'status': incident.get('status', 'unknown'),
                'impact': incident.get('impact', 'none'),
                'created_at': incident.get('created_at', ''),
                'updated_at': incident.get('updated_at', ''),
                'monitoring_at': incident.get('monitoring_at', ''),
                'resolved_at': incident.get('resolved_at', ''),
                'latest_update': latest_update.get('body', ''),
                'affected_components': self._get_affected_components(incident)
            })
        
        incident_df = pd.DataFrame(incident_data)
        
        return component_df, incident_df
    
    def _get_affected_components(self, incident: Dict) -> str:
        """
        Extract affected component names from an incident.
        
        Args:
            incident: Incident dictionary
            
        Returns:
            Comma-separated string of affected component names
        """
        affected_components = []
        
        # Look for affected components in different formats
        # Some incidents have direct affected_components list
        if 'affected_components' in incident:
            for comp in incident['affected_components']:
                affected_components.append(comp.get('name', ''))
        
        # Others might have it in incident updates
        for update in incident.get('incident_updates', []):
            if 'affected_components' in update:
                for comp in update['affected_components']:
                    affected_components.append(comp.get('name', ''))
        
        return ', '.join(list(set(filter(None, affected_components))))
    
    def generate_reliability_report(self, output_file: str = 'snowflake_reliability_report.xlsx') -> None:
        """
        Generate a comprehensive reliability report as an Excel file.
        
        Args:
            output_file: Path to save the Excel report
        """
        # Get reliability data
        component_df, incident_df = self.analyze_reliability()
        
        # Add calculation of uptime percentage based on incidents
        # This is a simplified calculation and might need refinement
        now = datetime.now()
        lookback_period = timedelta(days=self.days_lookback)
        total_components = len(component_df)
        
        # Convert datetime strings to datetime objects
        if not incident_df.empty:
            for col in ['created_at', 'resolved_at']:
                if col in incident_df.columns:
                    incident_df[col] = pd.to_datetime(incident_df[col], errors='coerce')
            
            # Calculate downtime per component
            component_downtime = {}
            for _, incident in incident_df.iterrows():
                # Skip if no resolved_at (ongoing incidents)
                if pd.isnull(incident['resolved_at']):
                    continue
                    
                # Calculate incident duration
                duration = incident['resolved_at'] - incident['created_at']
                
                # Add downtime to each affected component
                affected_components = incident['affected_components'].split(', ')
                for component in affected_components:
                    if component not in component_downtime:
                        component_downtime[component] = timedelta(0)
                    component_downtime[component] += duration
            
            # Calculate uptime percentage and add to component_df
            total_period = lookback_period.total_seconds()
            uptime_data = []
            
            for _, component in component_df.iterrows():
                name = component['name']
                if name in component_downtime:
                    downtime_seconds = component_downtime[name].total_seconds()
                    uptime_percent = 100 * (1 - (downtime_seconds / total_period))
                else:
                    uptime_percent = 100.0
                
                uptime_data.append({
                    'component_name': name,
                    'uptime_percentage': round(uptime_percent, 4),
                    'current_status': component['status']
                })
            
            uptime_df = pd.DataFrame(uptime_data)
        else:
            # If no incidents, all components have 100% uptime
            uptime_df = pd.DataFrame({
                'component_name': component_df['name'],
                'uptime_percentage': 100.0,
                'current_status': component_df['status']
            })
        
        # Get scheduled maintenance events
        try:
            status_data = self.get_current_status()
            maintenance_events = status_data.get('scheduled_maintenances', [])
            
            maintenance_data = []
            for event in maintenance_events:
                maintenance_data.append({
                    'name': event.get('name', 'Unknown Maintenance'),
                    'status': event.get('status', 'unknown'),
                    'scheduled_for': event.get('scheduled_for', ''),
                    'scheduled_until': event.get('scheduled_until', ''),
                    'impact': event.get('impact', 'none'),
                    'affected_components': self._get_affected_components(event)
                })
            
            maintenance_df = pd.DataFrame(maintenance_data)
        except Exception as e:
            logger.error(f"Error processing maintenance events: {str(e)}")
            maintenance_df = pd.DataFrame()
        
        # Create Excel writer
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Write summary sheet
            summary_data = {
                'Metric': [
                    'Report Date', 
                    'Period Covered', 
                    'Number of Components Monitored', 
                    'Components with Incidents', 
                    'Total Incidents', 
                    'Average Uptime Percentage'
                ],
                'Value': [
                    now.strftime('%Y-%m-%d'),
                    f"{(now - lookback_period).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
                    total_components,
                    len(component_downtime) if 'component_downtime' in locals() else 0,
                    len(incident_df),
                    uptime_df['uptime_percentage'].mean() if not uptime_df.empty else 100.0
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Write component sheet
            component_df.to_excel(writer, sheet_name='Components', index=False)
            
            # Write incidents sheet
            if not incident_df.empty:
                incident_df.to_excel(writer, sheet_name='Incidents', index=False)
            
            # Write uptime sheet
            uptime_df.to_excel(writer, sheet_name='Uptime', index=False)
            
            # Write maintenance sheet
            if not maintenance_df.empty:
                maintenance_df.to_excel(writer, sheet_name='Scheduled Maintenance', index=False)
        
        logger.info(f"Reliability report generated successfully: {output_file}")


# Example usage
if __name__ == "__main__":
    # Create the scraper with 180 days lookback
    scraper = SnowflakeStatusScraper(days_lookback=180)
    
    # Generate the reliability report
    scraper.generate_reliability_report()
    
    # Print current status overview
    status = scraper.get_current_status()
    print(f"Current Snowflake Status: {status['status']['description']}")
    
    # Count components by status
    if 'components' in status:
        status_counts = {}
        for component in status['components']:
            comp_status = component.get('status', 'unknown')
            if comp_status not in status_counts:
                status_counts[comp_status] = 0
            status_counts[comp_status] += 1
        
        print("\nComponent Status Summary:")
        for status_name, count in status_counts.items():
            print(f"  {status_name}: {count}")
    
    # Count ongoing incidents
    if 'incidents' in status:
        print(f"\nOngoing Incidents: {len(status['incidents'])}")
        for incident in status['incidents']:
            print(f"  {incident.get('name', 'Unknown')}: {incident.get('status', 'unknown')}")