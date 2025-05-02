import pandas as pd
import os
import logging
import json
import concurrent.futures
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import OpenAI if available
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    logging.warning("OpenAI package not found. Using fallback categorization.")

logger = logging.getLogger(__name__)

class IncidentAnalyzer:
    """
    Analyzes incidents to identify categories, trends, and patterns.
    Uses OpenAI GPT or fallback methods for categorization.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the analyzer with an OpenAI client for categorizing incidents.
        
        Args:
            openai_api_key: API key for OpenAI. If None, tries to use environment variable.
        """
        self.openai_client = None
        if OpenAI:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def categorize_incidents(self, incidents_df: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize incidents based on their titles and summaries.
        Uses OpenAI if available, otherwise uses keyword-based categorization.
        
        Args:
            incidents_df: DataFrame containing incident information
            
        Returns:
            DataFrame with added 'category' column
        """
        logger.info(f"Categorizing {len(incidents_df)} incidents")
        
        # If the DataFrame is empty, return it as is
        if incidents_df.empty:
            return incidents_df
        
        # Check if any incidents already have a category
        if 'category' in incidents_df.columns and incidents_df['category'].notna().all():
            logger.info("All incidents already categorized")
            return incidents_df
            
        # Function to categorize a single incident
        def categorize_incident(incident: pd.Series) -> str:
            # Skip if the incident already has a category
            if 'category' in incident and pd.notna(incident['category']):
                return incident['category']
                
            title = incident['title'] if 'title' in incident else ""
            summary = incident['summary'] if 'summary' in incident else ""
            
            # If incident has "No incidents found" title, return the category as is
            if title == "No incidents found" and 'category' in incident:
                return incident['category']
                
            if self.openai_client:
                try:
                    # Prepare the prompt for OpenAI
                    prompt = f"""
                    Categorize the following incident from a status page into one of these categories:
                    - Network Issue
                    - Database Problem
                    - API Outage
                    - Authentication/Authorization Issue
                    - Scheduled Maintenance
                    - Performance Degradation
                    - Storage System Problem
                    - Third-party Service Dependency
                    - Security Incident
                    - Data Processing Issue
                    - UI/Console Problem
                    - Other (please specify)
                    
                    If you choose "Other", suggest a concise category name.
                    
                    Incident Title: {title}
                    Incident Summary: {summary}
                    
                    Return ONLY the category name, nothing else.
                    """
                    
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that categorizes cloud service incidents."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=50,
                        temperature=0.0  # Use 0 temperature for more deterministic results
                    )
                    
                    category = response.choices[0].message.content.strip()
                    return category
                except Exception as e:
                    logger.error(f"Error using OpenAI for categorization: {e}")
                    # Fall back to keyword-based categorization
            
            # Keyword-based categorization as fallback
            return self._keyword_categorize(title, summary)
                
        # Apply the categorization function to each incident
        # If the DataFrame has less than 50 rows, process sequentially
        if len(incidents_df) < 50:
            categories = [categorize_incident(incidents_df.iloc[i]) for i in range(len(incidents_df))]
        else:
            # Otherwise use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                categories = list(executor.map(categorize_incident, [incidents_df.iloc[i] for i in range(len(incidents_df))]))
        
        # Add the categories to the DataFrame
        incidents_df['category'] = categories
        
        return incidents_df
    
    def _keyword_categorize(self, title: str, summary: str) -> str:
        """
        Categorize an incident based on keywords in the title and summary.
        Used as a fallback when OpenAI is not available.
        
        Args:
            title: Incident title
            summary: Incident summary
            
        Returns:
            Category name
        """
        title_lower = title.lower()
        summary_lower = summary.lower()
        text = title_lower + " " + summary_lower
        
        # Define keywords for each category
        categories = {
            "Network Issue": ["network", "connectivity", "dns", "routing", "packet", "latency", "connection"],
            "Database Problem": ["database", "db", "query", "sql", "nosql", "mongo", "postgres", "mysql", "oracle"],
            "API Outage": ["api", "endpoint", "request", "response", "rest", "graphql", "grpc"],
            "Authentication/Authorization Issue": ["auth", "login", "password", "credentials", "permission", "access", "token", "oauth", "sso"],
            "Scheduled Maintenance": ["maintenance", "scheduled", "planned", "upgrade", "update", "downtime"],
            "Performance Degradation": ["performance", "slow", "degraded", "latency", "throughput", "response time"],
            "Storage System Problem": ["storage", "s3", "bucket", "file", "disk", "volume", "blob"],
            "Third-party Service Dependency": ["third-party", "vendor", "external", "dependency", "integration", "service provider"],
            "Security Incident": ["security", "vulnerability", "breach", "attack", "malicious", "exploit", "threat"],
            "Data Processing Issue": ["data", "processing", "pipeline", "etl", "analytics", "calculation", "computation"],
            "UI/Console Problem": ["ui", "interface", "console", "dashboard", "portal", "frontend", "display", "visualization"]
        }
        
        # Count keyword matches for each category
        scores = {category: 0 for category in categories}
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Find the category with the highest score
        max_score = max(scores.values())
        if max_score > 0:
            # If there's a tie, use the first category with the max score
            for category, score in scores.items():
                if score == max_score:
                    return category
        
        # If no keywords match, return "Other"
        return "Other"
    
    def generate_category_descriptions(self, incidents_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Generate descriptions for each incident category and find example incidents.
        
        Args:
            incidents_df: DataFrame with categorized incidents
            
        Returns:
            Dictionary mapping category names to their descriptions and example incidents
        """
        logger.info("Generating category descriptions")
        
        # Handle empty DataFrame
        if incidents_df.empty:
            return {"No Data": {
                "description": "No incident data was available for analysis.",
                "examples": [],
                "count": 0
            }}
        
        # Get unique categories
        categories = incidents_df['category'].unique()
        
        category_info = {}
        
        for category in categories:
            # Get incidents in this category
            category_incidents = incidents_df[incidents_df['category'] == category]
            
            # Select example incidents (up to 3)
            example_indices = category_incidents.index[:min(3, len(category_incidents))]
            
            # Select only columns that exist in the DataFrame
            columns_to_select = [col for col in ['company', 'title', 'summary'] if col in category_incidents.columns]
            
            if columns_to_select:
                examples = category_incidents.loc[example_indices][columns_to_select].to_dict('records')
            else:
                examples = []
            
            # Generate description
            if self.openai_client and examples and 'title' in examples[0]:
                try:
                    # Use OpenAI to generate a description
                    prompt = f"""
                    Write a concise description (2-3 sentences) for the following category of cloud service incidents:
                    
                    Category: {category}
                    
                    Here are some example incidents in this category:
                    {json.dumps(examples, indent=2)}
                    
                    Return ONLY the description, nothing else.
                    """
                    
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that describes categories of cloud service incidents."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=200,
                        temperature=0.3
                    )
                    
                    description = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"Error generating description for category {category}: {e}")
                    description = self._get_default_description(category)
            else:
                # Use default descriptions
                description = self._get_default_description(category)
                
            category_info[category] = {
                'description': description,
                'examples': examples,
                'count': len(category_incidents)
            }
            
        return category_info
    
    def _get_default_description(self, category: str) -> str:
        """
        Get a default description for a category when OpenAI is not available.
        
        Args:
            category: Category name
            
        Returns:
            Description string
        """
        default_descriptions = {
            "Network Issue": "Problems related to network connectivity, DNS resolution, or routing that impact service availability or performance. These can manifest as connection timeouts, packet loss, or complete service unavailability.",
            "Database Problem": "Issues affecting database systems including query performance, connection problems, data consistency, or complete database outages. These can significantly impact application functionality and data availability.",
            "API Outage": "Failures or performance problems with API endpoints, preventing clients from making successful requests or receiving appropriate responses. May affect specific endpoints or the entire API surface.",
            "Authentication/Authorization Issue": "Problems with user login, authentication services, or permission systems. May prevent users from accessing services or result in incorrect access control.",
            "Scheduled Maintenance": "Planned downtime for system upgrades, patches, or infrastructure changes. Usually announced in advance with expected duration and potential impact on services.",
            "Performance Degradation": "Situations where systems remain operational but exhibit slower response times, reduced throughput, or increased error rates. May affect user experience without causing complete outages.",
            "Storage System Problem": "Issues affecting data storage systems such as object stores, file systems, or block storage. Can result in data access failures, slow read/write operations, or capacity problems.",
            "Third-party Service Dependency": "Outages or problems with external services that the system depends on, causing cascading failures. The root cause is outside direct control of the service provider.",
            "Security Incident": "Events related to security vulnerabilities, breaches, or active attacks. May require emergency response and potentially affect service availability or data integrity.",
            "Data Processing Issue": "Problems with data pipelines, ETL processes, analytics systems, or computation services. Can result in missing, incomplete, or incorrect data outputs.",
            "UI/Console Problem": "Issues affecting user interfaces, dashboards, or management consoles. May limit the ability to view or control services without impacting the underlying functionality.",
            "No Data": "No incident data was available for analysis during the specified timeframe.",
            "Other": "Incidents that don't clearly fall into one of the standard categories. May represent rare issue types or unique combinations of problems."
        }
        
        return default_descriptions.get(category, f"Incidents related to {category.lower()}.")
    
    def analyze_trends(self, incidents_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze trends in incidents over time.
        
        Args:
            incidents_df: DataFrame with categorized incidents
            
        Returns:
            Dictionary containing trend information
        """
        logger.info("Analyzing incident trends")
        
        if incidents_df.empty:
            return {
                'message': 'No incidents to analyze',
                'incidents_by_week': [],
                'incidents_by_category': [],
                'incidents_by_company': [],
                'avg_incidents_per_week': 0,
                'top_categories': [],
                'most_impacted_companies': [],
                'trend_direction': 'unknown'
            }
            
        # Handle DataFrame with "No incidents found" placeholder
        if (incidents_df['title'] == "No incidents found").any():
            return {
                'message': 'Status pages did not provide analyzable incident data',
                'incidents_by_week': [],
                'incidents_by_category': [],
                'incidents_by_company': [],
                'avg_incidents_per_week': 0,
                'top_categories': [],
                'most_impacted_companies': [],
                'trend_direction': 'unknown'
            }
            
        # Convert date to datetime if it's not already
        if not pd.api.types.is_datetime64_dtype(incidents_df['date']):
            incidents_df['date'] = pd.to_datetime(incidents_df['date'])
            
        # Incident count over time (by week)
        try:
            incidents_df['week'] = incidents_df['date'].dt.isocalendar().week
            incidents_df['year'] = incidents_df['date'].dt.isocalendar().year
            incidents_df['year_week'] = incidents_df['year'].astype(str) + '-' + incidents_df['week'].astype(str)
            
            incidents_by_week = incidents_df.groupby('year_week').size().reset_index(name='count')
            incidents_by_week = incidents_by_week.sort_values('year_week')
        except Exception as e:
            logger.error(f"Error calculating incidents by week: {e}")
            incidents_by_week = pd.DataFrame(columns=['year_week', 'count'])
        
        # Incidents by category
        try:
            incidents_by_category = incidents_df.groupby('category').size().reset_index(name='count')
            incidents_by_category = incidents_by_category.sort_values('count', ascending=False)
        except Exception as e:
            logger.error(f"Error calculating incidents by category: {e}")
            incidents_by_category = pd.DataFrame(columns=['category', 'count'])
        
        # Incidents by company
        try:
            incidents_by_company = incidents_df.groupby('company').size().reset_index(name='count')
            incidents_by_company = incidents_by_company.sort_values('count', ascending=False)
        except Exception as e:
            logger.error(f"Error calculating incidents by company: {e}")
            incidents_by_company = pd.DataFrame(columns=['company', 'count'])
        
        # Average incidents per week
        try:
            avg_incidents_per_week = incidents_by_week['count'].mean()
        except Exception:
            avg_incidents_per_week = 0
        
        # Most common categories
        try:
            top_categories = incidents_by_category.head(5)['category'].tolist()
        except Exception:
            top_categories = []
        
        # Most impacted companies
        try:
            most_impacted_companies = incidents_by_company.head(5)['company'].tolist()
        except Exception:
            most_impacted_companies = []
        
        # Trend direction (increasing or decreasing)
        if len(incidents_by_week) >= 2:
            try:
                first_half = incidents_by_week['count'].iloc[:len(incidents_by_week)//2].mean()
                second_half = incidents_by_week['count'].iloc[len(incidents_by_week)//2:].mean()
                trend_direction = 'increasing' if second_half > first_half else 'decreasing'
            except Exception:
                trend_direction = 'unknown'
        else:
            trend_direction = 'unknown'
            
        return {
            'incidents_by_week': incidents_by_week.to_dict('records'),
            'incidents_by_category': incidents_by_category.to_dict('records'),
            'incidents_by_company': incidents_by_company.to_dict('records'),
            'avg_incidents_per_week': avg_incidents_per_week,
            'top_categories': top_categories,
            'most_impacted_companies': most_impacted_companies,
            'trend_direction': trend_direction
        }
        
    def compare_with_peers(self, target_company: str, incidents_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compare the target company's reliability with its peers.
        
        Args:
            target_company: Name of the target company
            incidents_df: DataFrame with incidents from all companies
            
        Returns:
            Dictionary containing comparison information
        """
        logger.info(f"Comparing {target_company} with peers")
        
        if incidents_df.empty:
            return {'message': 'No incidents to compare'}
            
        # Handle DataFrame with "No incidents found" placeholder
        if (incidents_df['title'] == "No incidents found").any():
            return {'message': 'Status pages did not provide analyzable incident data for comparison'}
            
        # Get incidents for the target company
        target_incidents = incidents_df[incidents_df['company'] == target_company]
        
        # Get incidents for peer companies
        peer_incidents = incidents_df[incidents_df['company'] != target_company]
        
        # If either is empty, return a message
        if target_incidents.empty:
            return {'message': f'No incidents found for {target_company}'}
        if peer_incidents.empty:
            return {'message': 'No peer company incidents to compare with'}
            
        # Count incidents by company
        target_count = len(target_incidents)
        peer_companies = peer_incidents['company'].unique()
        
        if len(peer_companies) == 0:
            return {'message': 'No peer companies with incident data'}
            
        peer_counts = {company: len(peer_incidents[peer_incidents['company'] == company]) for company in peer_companies}
        avg_peer_count = sum(peer_counts.values()) / len(peer_counts)
        
        # Incident categories comparison
        try:
            target_categories = target_incidents.groupby('category').size().to_dict()
            peer_categories = peer_incidents.groupby('category').size().to_dict()
            
            # Normalize peer categories by number of companies
            peer_categories_normalized = {category: count / len(peer_companies) for category, count in peer_categories.items()}
            
            # Calculate category differences
            category_differences = {}
            all_categories = set(target_categories.keys()) | set(peer_categories.keys())
            
            for category in all_categories:
                target_count = target_categories.get(category, 0)
                peer_count_norm = peer_categories_normalized.get(category, 0)
                difference = target_count - peer_count_norm
                category_differences[category] = difference
                
            # Find categories where target company is doing better or worse
            better_categories = [category for category, diff in category_differences.items() if diff < 0]
            worse_categories = [category for category, diff in category_differences.items() if diff > 0]
        except Exception as e:
            logger.error(f"Error computing category differences: {e}")
            better_categories = []
            worse_categories = []
            category_differences = {}
        
        return {
            'target_incident_count': target_count,
            'avg_peer_incident_count': avg_peer_count,
            'peer_incident_counts': peer_counts,
            'relative_position': 'better' if target_count < avg_peer_count else 'worse',
            'category_differences': category_differences,
            'better_categories': better_categories,
            'worse_categories': worse_categories
        }