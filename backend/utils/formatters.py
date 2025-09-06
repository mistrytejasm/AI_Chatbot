import re
import json
from typing import List, Dict, Any


class ResponseFormatter:
    """Format AI responses for better readability and structure"""

    @staticmethod
    def format_response(content: str) -> str:
        """Format the AI response to be more structured and readable"""
        if not content:
            return content

        # Clean up the content
        content = content.strip()

        # Remove excessive table formatting artifacts
        content = re.sub(r'^\|[-\s:]+\|$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[-\s]{3,}$', '', content, flags=re.MULTILINE)

        # Apply formatting rules
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
    def extract_urls_from_search_results(search_results: str) -> List[str]:
        """Extract URLs from search results"""
        try:
            print(f"🔍 Extracting URLs from: {search_results[:200]}...")

            if isinstance(search_results, str):
                # Try to evaluate the string as Python literal
                try:
                    results = eval(search_results)
                except:
                    # If eval fails, try to parse as JSON
                    try:
                        results = json.loads(search_results)
                    except:
                        print("❌ Failed to parse search results")
                        return []
            else:
                results = search_results

            if isinstance(results, list):
                urls = []
                for item in results:
                    if isinstance(item, dict):
                        if "url" in item:
                            urls.append(item["url"])
                            print(f"✅ Found URL: {item['url']}")
                        elif "source" in item and isinstance(item["source"], str):
                            urls.append(item["source"])
                            print(f"✅ Found source: {item['source']}")

                print(f"🔗 Total URLs extracted: {len(urls)}")
                return urls

            print("❌ Search results is not a list")
            return []

        except Exception as e:
            print(f"❌ Error extracting URLs: {e}")
            return []

    @staticmethod
    def safe_json_dumps(data: Any) -> str:
        """Safely convert data to JSON string"""
        try:
            return json.dumps(data)
        except Exception:
            return json.dumps(str(data))
