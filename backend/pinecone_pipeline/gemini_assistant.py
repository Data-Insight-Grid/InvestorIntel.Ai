import os
import traceback
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

class GeminiAssistant:
    """
    A class that processes user queries and Pinecone search results with Gemini 2.0
    to generate relevant insights.
    """
    
    def __init__(self):
        """Initialize the GeminiAssistant with API key and model configuration."""
        
        # Load API key from environment variables
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Set default model to Gemini 2.0 Flash
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        # Minimum relevance threshold
        self.min_relevance_threshold = 0.2
        
        # Configure the Gemini API
        try:
            genai.configure(api_key=self.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini API configured successfully with model: {self.model_name}")
        except Exception as e:
            print(f"Failed to configure Gemini API: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Failed to configure Gemini API: {str(e)}")
    
    def process_query_with_results(self, query: str, search_results: list):
        """
        Process a query with search results from multiple sources and generate a response using Gemini.
        
        Args:
            query: The query string
            search_results: List of search results from both startup data and report data
        
        Returns:
            Generated response from Gemini
        """
        # Format the context based on the result sources
        formatted_context = []
        
        # Count sources to inform the model what kind of data we're presenting
        startup_count = sum(1 for r in search_results if r.get("source") == "startup")
        report_count = sum(1 for r in search_results if r.get("source") == "deloitte-report")
        
        # Add a context header to help the model understand the data
        if startup_count > 0 and report_count > 0:
            formatted_context.append(
                f"The following information comes from both startup data ({startup_count} results) and " +
                f"Deloitte industry reports ({report_count} results):"
            )
        elif startup_count > 0:
            formatted_context.append(f"The following information comes from startup data ({startup_count} results):")
        elif report_count > 0:
            formatted_context.append(f"The following information comes from Deloitte industry reports ({report_count} results):")
        
        # Process and format each result
        for i, result in enumerate(search_results):
            if result.get("source") == "startup":
                # Format startup data
                formatted_context.append(
                    f"Result #{i+1} (Startup): {result.get('startup_name', 'Unnamed Startup')}\n" +
                    f"Industry: {result.get('industry', 'Unknown')}\n" +
                    f"Content: {result.get('text', 'No information available')}\n"
                )
            elif result.get("source") == "deloitte-report":
                # Format Deloitte report data
                formatted_context.append(
                    f"Result #{i+1} (Industry Report): {result.get('report_title', 'Untitled Report')}\n" +
                    f"Industry: {result.get('industry', 'Unknown')}\n" +
                    f"Year: {result.get('year', 'Unknown')}\n" +
                    f"Content: {result.get('text', 'No information available')}\n"
                )
        
        # Join all context pieces with separators
        context_text = "\n\n".join(formatted_context)
        
        # Prepare system prompt
        system_prompt = """
        You are an AI assistant for venture capitalists and investors. 
        When answering questions, use the provided search results to inform your responses.
        Provide factual, accurate information based directly on the search results.
        If the information comes from multiple sources, synthesize it coherently.
        
        Guidelines:
        - Cite specific sources when providing information (e.g., "According to Result #3...")
        - If a question can't be answered with the provided results, say so clearly
        - Be concise and focus on investment-relevant points
        - For startups, highlight business model, market potential, and competitive advantages
        - For industry reports, focus on market trends, growth forecasts, and key insights
        """
        
        # Generate content with Gemini
        try:
            # Combine system prompt with user query since Gemini doesn't support system messages
            combined_prompt = f"""
            {system_prompt}
            
            Based on the following search results, please answer this question: {query}
            
            {context_text}
            """
            
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [combined_prompt]}
                ]
            )
            return response.text
        except Exception as e:
            print(f"Error generating Gemini response: {e}")
            return "I'm unable to process this request at the moment. Please try again with a different question."
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Format search results from Pinecone into a context string for Gemini.
        
        Args:
            search_results: List of search results from Pinecone
            
        Returns:
            str: Formatted context string
        """
        formatted_results = []
        
        for i, result in enumerate(search_results, 1):
            # Extract key information from the result
            startup_name = result.get("startup_name", "Unknown")
            industry = result.get("industry", "Unknown Industry")
            content = result.get("text", "No content available")
            
            # Check if content is empty or None and provide a placeholder
            if not content or content.strip() == "":
                content = "No content available for this startup."
            
            # Format the result without score or length information
            formatted_result = f"""
RESULT #{i}:
Startup: {startup_name}
Industry: {industry}

{content}
---
"""
            formatted_results.append(formatted_result)
        
        # Combine all formatted results into a single string
        context = "\n".join(formatted_results)
        return context
    
    def _clean_response_format(self, text: str) -> str:
        """
        Clean up response formatting for better presentation.
        
        Args:
            text: The raw response from Gemini
            
        Returns:
            str: Cleaned and formatted response
        """
        # Remove any introductory phrases
        text = text.strip()
        
        # List of common introductory phrases to remove
        intros = [
            "Based on the provided search results:",
            "Based on the search results provided:",
            "Here's the information from the search results:",
            "According to the search results:",
            "Here's what I found in the search results:",
            "From the search results:",
            ", here's the information about",
            ", here's what is known about",
            "The search results indicate that",
            "The information available from the search results shows"
        ]
        
        for intro in intros:
            if text.lower().startswith(intro.lower()):
                text = text[len(intro):].strip()
        
        # Remove all result references
        text = re.sub(r'\(Result #\d+\)', '', text)
        text = re.sub(r'\(Source \d+\)', '', text)
        
        # Fix bullet point formatting line by line
        lines = text.split('\n')
        formatted_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                formatted_lines.append('')
                i += 1
                continue
                
            # Fix bullet points at the start of lines
            if line.startswith('*') or line.startswith('-'):
                line = '• ' + line[1:].strip()
                
            # Check for multiple bullets on the same line
            if '• ' in line and not line.startswith('• '):
                # This line has bullets but doesn't start with one
                parts = re.split(r'(• )', line)
                new_parts = []
                
                for j, part in enumerate(parts):
                    if part == '• ' and j > 0 and parts[j-1].strip() and j+1 < len(parts):
                        # This is a bullet in the middle of text
                        new_parts.append('\n• ')
                    else:
                        new_parts.append(part)
                
                line = ''.join(new_parts)
                
            # Add the processed line
            formatted_lines.append(line)
            i += 1
        
        # Join lines and clean up spacing
        text = '\n'.join(formatted_lines)
        
        # Fix any remaining bullet point issues
        text = text.replace('\n• ', '\n• ')  # Ensure consistent spacing
        text = re.sub(r'([^\n])• ', r'\1\n• ', text)  # Add line break before bullets
        text = re.sub(r'\n{3,}', '\n\n', text)  # No more than 2 consecutive line breaks
        
        return text.strip()
    