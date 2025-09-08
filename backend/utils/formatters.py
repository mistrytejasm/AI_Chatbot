import re
import json
from typing import List, Dict, Any


class ResponseFormatter:
    """Format AI responses for better readability and structure"""

    @staticmethod
    def format_response_with_citations(content: str, urls: list) -> str:
        """Format response and add citation numbers based on available URLs"""
        if not content or not urls:
            return ResponseFormatter.format_response(content)
        
        # First apply regular formatting
        formatted_content = ResponseFormatter.format_response(content)
        
        # Add citations at the end of sentences that likely reference sources
        # This is a simple implementation - you can make it more sophisticated
        citation_patterns = [
            r'(\. )(?=[A-Z])',  # End of sentences
            r'(\w+)(\.)(\s+)',   # Word followed by period and space
        ]
        
        # Simple citation insertion - add citations to key statements
        # You can enhance this logic based on your needs
        sentences = formatted_content.split('. ')
        cited_content = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                # Add citation to sentences that seem to contain factual information
                if any(keyword in sentence.lower() for keyword in ['according', 'reported', 'study', 'research', 'data', 'statistics']):
                    citation_num = min(i + 1, len(urls))  # Ensure we don't exceed available URLs
                    sentence += f'[{citation_num}]'
                cited_content.append(sentence)
        
        return '. '.join(cited_content)

    # Keep all your existing methods unchanged...
    @staticmethod
    def format_response(content: str) -> str:
        """Format the AI response to be more structured and readable"""
        # Your existing implementation
        if not content:
            return content

        content = content.strip()
        content = re.sub(r'^\|[-\s:]+\|$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[-\s]{3,}$', '', content, flags=re.MULTILINE)
        
        content = ResponseFormatter._ensure_proper_headers(content)
        content = ResponseFormatter._format_lists(content)
        content = ResponseFormatter._format_paragraphs(content)
        content = ResponseFormatter._clean_whitespace(content)
        
        return content
    
    @staticmethod
    def _clean_whitespace(content: str) -> str:
        """Clean up whitespace issues"""
        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split('\n')]

        # Remove multiple empty lines but keep paragraph breaks
        cleaned_lines = []
        empty_count = 0

        for line in lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 1:  # Allow max 1 consecutive empty line
                    cleaned_lines.append('')
            else:
                empty_count = 0
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    @staticmethod
    def _ensure_proper_headers(content: str) -> str:
        """Ensure headers are properly formatted"""
        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            stripped = line.strip()

            # Convert double asterisks headers to proper markdown headers
            if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
                header_text = stripped[2:-2].strip()
                # Don't convert if it's just bold text in middle of sentence
                if not any(char in header_text for char in ['.', ',', ';']):
                    formatted_lines.append(f"## {header_text}")
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    @staticmethod
    def _format_lists(content: str) -> str:
        """Format bullet points and lists"""
        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            stripped = line.strip()

            # Convert numbered points to proper bullet points
            if re.match(r'^\d+\.\s+', stripped):
                # Keep numbered lists as is
                formatted_lines.append(line)
            elif re.match(r'^[-•·]\s+', stripped):
                # Clean up bullet points
                formatted_lines.append(f"• {stripped[2:].strip()}")
            elif re.match(r'^\*\s+', stripped):
                # Convert asterisk to bullet
                formatted_lines.append(f"• {stripped[2:].strip()}")
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    @staticmethod
    def _format_paragraphs(content: str) -> str:
        """Format paragraphs for better readability"""
        # Ensure proper spacing between sections
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Add spacing after headers
        content = re.sub(r'(#{1,6}\s+[^\n]+)\n(?!\n)', r'\1\n\n', content)

        return content

    @staticmethod
    def _clean_whitespace(content: str) -> str:
        """Clean up whitespace issues"""
        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split('\n')]

        # Remove multiple empty lines but keep paragraph breaks
        cleaned_lines = []
        empty_count = 0

        for line in lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:  # Allow max 2 consecutive empty lines
                    cleaned_lines.append(line)
            else:
                empty_count = 0
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    @staticmethod
    def extract_urls_from_search_results(search_results_content):
        """Extract URLs from Tavily search results"""
        try:
            # Handle both string and dict inputs
            if isinstance(search_results_content, str):
                # Try to parse as JSON if it's a string
                import json
                try:
                    search_data = json.loads(search_results_content)
                except json.JSONDecodeError:
                    # If not JSON, try to evaluate as Python literal
                    import ast
                    try:
                        search_data = ast.literal_eval(search_results_content)
                    except (ValueError, SyntaxError):
                        print("❌ Could not parse search results string")
                        return []
            else:
                search_data = search_results_content

            # Debug: Print the structure
            print(f"🔍 Search data type: {type(search_data)}")
            if isinstance(search_data, dict):
                print(f"🔍 Available keys: {list(search_data.keys())}")

            # Extract URLs from the correct structure
            if isinstance(search_data, dict) and 'results' in search_data:
                results = search_data['results']
                print(f"🔍 Results type: {type(results)}, length: {len(results) if isinstance(results, list) else 'N/A'}")
                
                if isinstance(results, list):
                    urls = []
                    for item in results:
                        if isinstance(item, dict) and 'url' in item:
                            urls.append(item['url'])
                    print(f"🔗 Successfully extracted {len(urls)} URLs")
                    return urls
                else:
                    print("❌ 'results' key exists but contains non-list data")
                    return []
            else:
                print("❌ Search data missing 'results' key or not a dictionary")
                return []

        except Exception as e:
            print(f"❌ Error extracting URLs: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def safe_json_dumps(data: Any) -> str:
        """Safely convert data to JSON string"""
        try:
            return json.dumps(data)
        except Exception:
            return json.dumps(str(data))
